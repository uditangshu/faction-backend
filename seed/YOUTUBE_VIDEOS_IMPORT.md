# YouTube Videos CSV Import Guide

## File Location
`seed/youtube_videos.csv`

## CSV Structure

The CSV includes the following columns:
- `id`: UUID (primary key)
- `chapter_id`: UUID (foreign key to chapter table)
- `subject_id`: UUID (foreign key to subject table)
- `youtube_video_id`: YouTube video ID (extracted from URL)
- `youtube_url`: Full YouTube video URL
- `title`: Video title (max 200 characters)
- `description`: Video description (optional)
- `thumbnail_url`: Video thumbnail URL (optional)
- `duration_seconds`: Video duration in seconds (optional)
- `order`: Order/sequence within chapter (default: 0)
- `is_active`: Whether video is active (default: true)
- `views_count`: Number of views (default: 0)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

## Important Notes

⚠️ **Before Importing:**

1. **Replace Foreign Key IDs**: The `chapter_id` and `subject_id` values in the CSV are placeholder UUIDs. You must replace them with actual IDs from your `chapter` and `subject` tables.

2. **Replace YouTube Video IDs**: The YouTube video IDs are examples. Replace them with real YouTube video IDs from actual videos you want to include.

3. **Verify YouTube URLs**: Ensure the YouTube URLs match the video IDs and are valid.

## How to Import to Supabase

### Method 1: Using Supabase Dashboard

1. Go to your Supabase project dashboard
2. Navigate to **Table Editor**
3. Select the `youtube_videos` table
4. Click **Insert** → **Import data from CSV**
5. Upload the `youtube_videos.csv` file
6. Map the columns (should auto-detect)
7. Review and confirm import

### Method 2: Using SQL Editor

1. Go to **SQL Editor** in Supabase
2. Use the following SQL template (after updating the data):

```sql
INSERT INTO youtube_videos (
    id, chapter_id, subject_id, youtube_video_id, youtube_url,
    title, description, thumbnail_url, duration_seconds,
    order, is_active, views_count, created_at, updated_at
) VALUES
-- Copy values from CSV here
```

### Method 3: Using Supabase CLI

```bash
# If you have Supabase CLI installed
supabase db import youtube_videos.csv
```

## Updating the CSV

To customize the data:

1. **Get Real Chapter IDs**: Query your database:
   ```sql
   SELECT id, name FROM chapter;
   ```

2. **Get Real Subject IDs**: Query your database:
   ```sql
   SELECT id, name FROM subject;
   ```

3. **Replace Placeholder UUIDs**: Update the CSV with actual IDs

4. **Add Real YouTube Videos**: 
   - Get YouTube video IDs from actual YouTube URLs
   - Update `youtube_video_id` and `youtube_url` columns
   - Generate thumbnail URLs: `https://img.youtube.com/vi/{VIDEO_ID}/maxresdefault.jpg`

## Sample Data

The CSV includes 20 sample videos covering:
- Physics (Motion, Forces, Thermodynamics, Electromagnetism, Waves, Optics)
- Chemistry (Atoms, Reactions, Organic Chemistry, Acids/Bases, Bonding, Periodic Table)
- Mathematics (Algebra, Calculus, Trigonometry, Coordinate Geometry)
- Biology (Cell Structure, Genetics, Anatomy, Plant Biology)

Each video has:
- Unique UUID
- Realistic titles and descriptions
- Thumbnail URLs
- Duration in seconds
- View counts
- Proper ordering within chapters

## Validation

Before importing, ensure:
- ✅ All UUIDs are valid format
- ✅ `chapter_id` exists in `chapter` table
- ✅ `subject_id` exists in `subject` table
- ✅ `youtube_video_id` is a valid YouTube video ID
- ✅ `youtube_url` matches the video ID
- ✅ `title` is under 200 characters
- ✅ `duration_seconds` is a positive integer (if provided)
- ✅ `order` is a non-negative integer
- ✅ Timestamps are in valid format: `YYYY-MM-DD HH:MM:SS`

