"""Rating calculation service using Elo-based system"""

import math
from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.contest import ContestLeaderboard
from app.models.user import User


def win_prob(ra: float, rb: float) -> float:
    """
    Calculate win probability of player A against player B using Elo formula.
    
    Args:
        ra: Rating of player A
        rb: Rating of player B
        
    Returns:
        Win probability (0.0 to 1.0)
    """
    return 1 / (1 + 10 ** ((rb - ra) / 400))


def expected_rank(rating: float, all_ratings: List[float]) -> float:
    """
    Calculate expected rank for a player based on their rating.
    
    Args:
        rating: Player's rating
        all_ratings: List of all other players' ratings
        
    Returns:
        Expected rank (higher number = worse rank)
    """
    rank = 1.0
    for r in all_ratings:
        rank += win_prob(r, rating)
    return rank


def find_rating_for_rank(target_rank: float, all_ratings: List[float]) -> float:
    """
    Binary search to find rating that would give target expected rank.
    
    Args:
        target_rank: Desired expected rank
        all_ratings: List of all other players' ratings
        
    Returns:
        Target rating
    """
    lo, hi = 0, 4000  # rating bounds
    for _ in range(50):  # enough precision
        mid = (lo + hi) / 2
        er = expected_rank(mid, all_ratings)
        if er > target_rank:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def damping(k: int) -> float:
    """
    Calculate damping factor based on number of contests participated.
    More contests = less rating change per contest.
    
    Args:
        k: Number of contests participated
        
    Returns:
        Damping factor (between 2/9 and 1)
    """
    return max(2/9, 1 / (2 + 0.5 * k))


def absence_penalty(rating: int) -> int:
    """
    Calculate penalty for not participating in contest.
    Currently returns rating unchanged (no penalty).
    
    Args:
        rating: Current rating
        
    Returns:
        Rating after penalty (currently unchanged)
    """
    return rating - 0


def update_ratings(players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Update ratings for all players using Elo-based system.
    
    Steps:
    1. Calculate expected rank for each player
    2. Calculate geometric mean of expected and actual rank
    3. Find target rating for each player
    4. Apply damped update based on contest participation
    
    Args:
        players: List of player dicts with keys:
            - "id": Player ID
            - "rating": Current rating (int)
            - "rank": Actual rank in contest (int)
            - "contests": Number of contests participated (int)
    
    Returns:
        Updated list of players with new fields:
            - "expected_rank": Expected rank based on rating
            - "mean_rank": Geometric mean of expected and actual rank
            - "target_rating": Target rating for mean rank
            - "new_rating": Final updated rating
    """
    ratings = [p["rating"] for p in players]
    
    # Step 1: Calculate expected ranks
    for p in players:
        others = [r for r in ratings if r != p["rating"]]
        p["expected_rank"] = expected_rank(p["rating"], others)
    
    # Step 2: Calculate geometric mean rank
    for p in players:
        p["mean_rank"] = math.sqrt(p["expected_rank"] * p["rank"])
    
    # Step 3: Find target rating for each player
    for p in players:
        others = [r for r in ratings if r != p["rating"]]
        p["target_rating"] = find_rating_for_rank(p["mean_rank"], others)
    
    # Step 4: Apply damped update
    for p in players:
        delta = p["target_rating"] - p["rating"]
        f = damping(p["contests"])
        p["new_rating"] = round(p["rating"] + f * delta)
        p["rating_delta"] = p["new_rating"] - p["rating"]
    
    return players


async def calculate_contest_ratings(
    db: AsyncSession,
    contest_id: UUID,
) -> bool:
    """
    Calculate and update ratings for all participants in a contest.
    
    Args:
        db: Database session
        contest_id: Contest ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get all leaderboard entries for this contest, ordered by score (descending)
        result = await db.execute(
            select(ContestLeaderboard)
            .where(ContestLeaderboard.contest_id == contest_id)
            .order_by(desc(ContestLeaderboard.score))
        )
        leaderboard_entries = result.scalars().all()
        
        if not leaderboard_entries:
            return True  # No participants
        
        # Assign ranks (handle ties - same score = same rank)
        current_rank = 1
        prev_score = None
        for i, entry in enumerate(leaderboard_entries):
            if prev_score is not None and entry.score < prev_score:
                # Different score, update rank
                current_rank = i + 1
            # Same score gets same rank (current_rank stays the same)
            entry.rank = current_rank
            prev_score = entry.score
        
        # Get user IDs and fetch user data (for current rating and contest count)
        user_ids = [entry.user_id for entry in leaderboard_entries]
        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = {user.id: user for user in users_result.scalars().all()}
        
        # Count previous contests for each user (excluding current contest)
        contest_counts = {}
        for user_id in user_ids:
            count_result = await db.execute(
                select(func.count(ContestLeaderboard.id))
                .where(
                    ContestLeaderboard.user_id == user_id,
                    ContestLeaderboard.contest_id != contest_id
                )
            )
            contest_counts[user_id] = count_result.scalar() or 0
        
        # Prepare players list for rating calculation
        players = []
        for entry in leaderboard_entries:
            user = users.get(entry.user_id)
            if not user:
                continue
            
            players.append({
                "id": str(entry.user_id),
                "rating": user.current_rating,
                "rank": entry.rank,
                "contests": contest_counts[entry.user_id],
                "entry": entry,  # Keep reference to update later
                "user": user,  # Keep reference to update user rating
            })
        
        if not players:
            return True
        
        # Calculate new ratings
        updated_players = update_ratings(players)
        
        # Update leaderboard entries and user ratings
        for player in updated_players:
            entry = player["entry"]
            user = player["user"]
            
            # Update leaderboard entry
            entry.rating_before = player["rating"]
            entry.rating_after = player["new_rating"]
            entry.rating_delta = player["rating_delta"]
            
            # Update user rating
            user.current_rating = player["new_rating"]
            if player["new_rating"] > user.max_rating:
                user.max_rating = player["new_rating"]
        
        await db.commit()
        return True
        
    except Exception as e:
        await db.rollback()
        raise e

