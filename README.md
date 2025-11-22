<!-- # Tapeciarnia - Dynamic Wallpaper App

A cross-platform application for setting dynamic video and image wallpapers with an organized collection system.

## Features
- Set video wallpapers (MP4, MKV, WebM, AVI, MOV)
- Set image wallpapers (JPG, PNG, BMP, GIF)
- Drag & drop support for local files
- Scheduled wallpaper rotation with customizable intervals
- Organized collection management (Videos, Images, Favorites)
- Cross-platform wallpaper engine (Weepe for Windows, mpv for Linux)
- System tray integration
- Auto-pause functionality during fullscreen applications
- Multi-language support

## Installation

### Prerequisites
- Python 3.8 or higher
- **Linux/Mac**: mpv media player (sudo apt install mpv or brew install mpv)
- **Windows**: Weepe (bundled in the application)

### Quick Setup
1. Clone the repository:
bash
git clone https://github.com/mh-Earth/Tapeciarnia.git
cd Tepeciarnia  
Create and activate virtual environment:

bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
Install dependencies:

bash
pip install -r requirements.txt
Run the application:

bash
python -m code.scripts.main
Project Structure
text
Tepeciarnia/
├── code/scripts/
│   ├── core/                 # Core application logic
│   │   ├── wallpaper_controller.py
│   │   ├── download_manager.py
│   │   ├── scheduler.py
│   │   └── autopause_controller.py
│   ├── ui/                   # User interface components
│   │   ├── main_window.py
│   │   ├── widgets.py
│   │   └── dialogs.py
│   ├── utils/                # Utility functions
│   │   ├── path_utils.py
│   │   ├── system_utils.py
│   │   ├── validators.py
│   │   └── file_utils.py
│   ├── models/               # Data models
│   │   └── config.py
│   └── main.py               # Application entry point
├── requirements.txt
└── README.md
Usage
Basic Operations
Load URL: Enter YouTube URL or image URL and click "Load"

Browse: Click "Browse wallpapers" to select local files

Drag & Drop: Drag files directly onto the app window

Start: Apply the current wallpaper from URL input

Reset: Restore system default wallpaper

Collection Management
Shuffle Animated: Randomly select and play a video wallpaper

Shuffle Wallpaper: Randomly select and apply an image wallpaper

My Collection: Use all wallpapers in your organized collection

Favorite Wallpapers: Use only your favorited wallpapers

Range Filter: Filter by All, Wallpaper (images only), or MP4 (videos only)

Automated Features
Scheduler: Enable automatic wallpaper rotation

Interval: Set rotation frequency (minutes)

Auto-pause: Automatically pauses wallpapers during fullscreen apps

Controls Overview
Control	Function
Start	Apply current wallpaper from URL input
Reset	Restore default system wallpaper
Shuffle Animated	Random video wallpaper from collection
Shuffle Wallpaper	Random image wallpaper from collection
Browse	Select local media files
Load	Download and apply from URL
My Collection	Use entire organized collection
Favorite Wallpapers	Use only favorited wallpapers
Range: All	Include both images and videos
Range: Wallpaper	Images only
Range: MP4	Videos only
Collection Organization
The app automatically organizes your wallpapers:

text
Pictures/Tapeciarnia/
├── Saves/           # Downloaded and added video and image wallpapers

└── Favorites/        # Your favorite wallpapers (both types)
Windows Specific Setup
For optimal Windows performance:

The app includes Weepe for proper video wallpaper functionality

Ensure code/scripts/bin/tools/weepe.exe exists

If Weepe is missing, the app falls back to mpv/ffplay fullscreen mode

Troubleshooting
Common Issues
Videos play in fullscreen instead of wallpaper: Ensure Weepe (Windows) or mpv+xwinwrap (Linux) is properly installed

Wallpaper doesn't apply: Verify file permissions and supported formats

Scheduler not working: Check if the source folder contains valid media files

Supported Formats
Video: MP4, MKV, WebM, AVI, MOV

Image: JPG, JPEG, PNG, BMP, GIF
 -->
