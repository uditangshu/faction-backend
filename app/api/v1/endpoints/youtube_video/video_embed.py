"""YouTube Video Embed Proxy Endpoint

This endpoint serves a self-contained HTML page that properly embeds YouTube videos
with correct Origin/Referer headers to avoid Error 153, and provides a postMessage
bridge for React Native to control playback.
"""

import re
from fastapi import APIRouter, Response, Query
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/video", tags=["Video Embed"])


def generate_embed_html(
    video_id: str,
    autoplay: bool = True,
    origin: str = "https://resilient-freedom-production.up.railway.app"
) -> str:
    """Generate the YouTube embed HTML with IFrame API integration."""
    
    autoplay_int = 1 if autoplay else 0
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="referrer" content="origin">
    <title>Video Player</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        html, body {{
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #000;
        }}
        #player-container {{
            position: relative;
            width: 100%;
            height: 100%;
        }}
        #player {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }}
        /* Overlay to cover YouTube logo in bottom-right corner */
        .yt-logo-cover {{
            position: absolute;
            bottom: 0;
            right: 0;
            width: 120px;
            height: 40px;
            background: transparent;
            z-index: 9999;
            pointer-events: auto;
        }}
        /* Cover the entire bottom area to block YouTube's progress bar when controls=0 */
        .bottom-cover {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 60px;
            background: transparent;
            z-index: 9998;
            pointer-events: auto;
        }}
        /* Cover top-left for any YouTube branding */
        .top-cover {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 50px;
            background: transparent;
            z-index: 9998;
            pointer-events: auto;
        }}
    </style>
</head>
<body>
    <div id="player-container">
        <div id="player"></div>
        <div class="top-cover"></div>
        <div class="bottom-cover"></div>
        <div class="yt-logo-cover"></div>
    </div>

    <script>
        // YouTube IFrame API
        var tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        var firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

        var player;
        var progressInterval;
        var isReady = false;

        function onYouTubeIframeAPIReady() {{
            player = new YT.Player('player', {{
                videoId: '{video_id}',
                playerVars: {{
                    'autoplay': {autoplay_int},
                    'controls': 0,
                    'modestbranding': 1,
                    'rel': 0,
                    'showinfo': 0,
                    'fs': 0,
                    'playsinline': 1,
                    'iv_load_policy': 3,
                    'disablekb': 1,
                    'origin': '{origin}'
                }},
                events: {{
                    'onReady': onPlayerReady,
                    'onStateChange': onPlayerStateChange,
                    'onError': onPlayerError
                }}
            }});
        }}

        function onPlayerReady(event) {{
            isReady = true;
            var duration = player.getDuration();
            sendToRN({{
                type: 'ready',
                duration: duration
            }});
            
            // Start progress updates
            startProgressUpdates();
            
            // Autoplay if requested
            if ({autoplay_int} === 1) {{
                event.target.playVideo();
            }}
        }}

        function onPlayerStateChange(event) {{
            var stateNames = {{
                [-1]: 'unstarted',
                [0]: 'ended',
                [1]: 'playing',
                [2]: 'paused',
                [3]: 'buffering',
                [5]: 'cued'
            }};
            
            var stateName = stateNames[event.data] || 'unknown';
            
            sendToRN({{
                type: 'stateChange',
                state: stateName,
                stateCode: event.data
            }});

            // Manage progress updates based on state
            if (event.data === YT.PlayerState.PLAYING) {{
                startProgressUpdates();
            }} else if (event.data === YT.PlayerState.PAUSED || event.data === YT.PlayerState.ENDED) {{
                stopProgressUpdates();
                // Send one final progress update
                sendProgress();
            }}
        }}

        function onPlayerError(event) {{
            var errorCodes = {{
                2: 'invalid_parameter',
                5: 'html5_error',
                100: 'video_not_found',
                101: 'embed_not_allowed',
                150: 'embed_not_allowed'
            }};
            
            sendToRN({{
                type: 'error',
                error: errorCodes[event.data] || 'unknown_error',
                errorCode: event.data
            }});
        }}

        function startProgressUpdates() {{
            stopProgressUpdates();
            progressInterval = setInterval(sendProgress, 250);
        }}

        function stopProgressUpdates() {{
            if (progressInterval) {{
                clearInterval(progressInterval);
                progressInterval = null;
            }}
        }}

        function sendProgress() {{
            if (player && isReady && typeof player.getCurrentTime === 'function') {{
                try {{
                    var currentTime = player.getCurrentTime();
                    var duration = player.getDuration();
                    var buffered = player.getVideoLoadedFraction() * duration;
                    
                    sendToRN({{
                        type: 'progress',
                        currentTime: currentTime,
                        duration: duration,
                        buffered: buffered
                    }});
                }} catch (e) {{
                    // Player might not be ready
                }}
            }}
        }}

        function sendToRN(data) {{
            try {{
                if (window.ReactNativeWebView) {{
                    window.ReactNativeWebView.postMessage(JSON.stringify(data));
                }}
            }} catch (e) {{
                console.error('Error sending to RN:', e);
            }}
        }}

        // Handle commands from React Native
        window.addEventListener('message', function(event) {{
            handleCommand(event.data);
        }});
        
        // Also handle for Android
        document.addEventListener('message', function(event) {{
            handleCommand(event.data);
        }});

        function handleCommand(dataStr) {{
            try {{
                var data = JSON.parse(dataStr);
                
                if (!player || !isReady) {{
                    return;
                }}

                switch (data.command) {{
                    case 'play':
                        player.playVideo();
                        break;
                    case 'pause':
                        player.pauseVideo();
                        break;
                    case 'seekTo':
                        player.seekTo(data.time, true);
                        break;
                    case 'setVolume':
                        player.setVolume(data.volume);
                        break;
                    case 'setPlaybackRate':
                        player.setPlaybackRate(data.rate);
                        break;
                    case 'mute':
                        player.mute();
                        break;
                    case 'unmute':
                        player.unMute();
                        break;
                    case 'getProgress':
                        sendProgress();
                        break;
                }}
            }} catch (e) {{
                console.error('Error handling command:', e);
            }}
        }}
    </script>
</body>
</html>'''


@router.get("/embed/{video_id}", response_class=HTMLResponse)
async def get_video_embed(
    video_id: str,
    autoplay: bool = Query(True, description="Autoplay video on load"),
):
    """
    Serve a YouTube embed HTML page with proper headers.
    
    This endpoint returns a self-contained HTML page that:
    - Sets proper Origin/Referer headers to avoid Error 153
    - Uses controls=0 to hide YouTube's native controls
    - Provides postMessage API for React Native to control playback
    - Covers YouTube branding with minimal overlays
    
    The React Native app should load this URL in a WebView and communicate
    via postMessage for play/pause/seek commands.
    """
    
    # Validate video_id format (YouTube video IDs are 11 characters)
    if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        return HTMLResponse(
            content="<html><body><h1>Invalid video ID</h1></body></html>",
            status_code=400
        )
    
    html_content = generate_embed_html(
        video_id=video_id,
        autoplay=autoplay,
        origin="https://faction-backend-production.up.railway.app"
    )
    
    return HTMLResponse(
        content=html_content,
        headers={
            "Content-Type": "text/html; charset=utf-8",
            "X-Frame-Options": "SAMEORIGIN",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
    )
