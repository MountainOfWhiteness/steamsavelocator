# Steam Save Locator

I whipped this up because finding save files on PC can be annoyingly complicated. Some games put them in Documents, others in AppData, some in the Steam installation folder. It's a mess. This tool just scans everything and tells you exactly where they are.

![Screenshot](screenshot.png)

### What's new in v0.3

I finally gave this a proper interface. It's now a standalone app with a dark theme, so no more dealing with command line windows.

I also added a "confidence" system which basically just flags folders green if they are definitely save files, and red if they might just be random game data. It helps filter out the noise if you have a lot of stuff installed.

### How to use

1. Grab the exe from the releases tab and run it. No install needed.
2. Hit the **Scan System** button.
3. If you want to find a specific game, just type its name in the search bar.
4. Click **Open** on any result to jump straight to the folder.

### Features

- **Finds everything**: Checks Documents, AppData, Steam Cloud path, and game install folders.
- **Smart Filters**: If you see too much junk, set the filter to "High Only" to see only confirmed saves.
- **Cloud Support**: Works with Steam Cloud saves too.

### Issues

If you run into any bugs or if it misses a game, feel free to [open an issue](https://github.com/MountainOfWhiteness/steamsavelocator/issues) and I'll take a look. Matches might not be perfect for every single Blackbeard game out there, but I tried to cover the most common ones like Goldberg.
