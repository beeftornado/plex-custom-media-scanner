plex-custom-media-scanner
=========================

Custom scanner to be used with Plex Media Server configured to recognize my Tivo recordings transferred with kmttg

## Features

The custom scanners are built on top of the stock ones included with Plex, so they are the same with additions:
* Added a regular expression for **matching a new video file** (eg. `Ep#112_Bad Wolf (Rec 08_19_2012).mp4, Blink (Rec 09_13_2012).mp4`)
  * It is the file format I use for my shows that I have transferred from my Tivo. If available it starts with the episode number, and then the episode title, and the recorded date
  * It uses the folder name as the series name
* If a **pytivo metadata** file is available for the video, it will use its information instead of guessing it from the file name.
  * pytivo is a separate service that runs and makes videos in a particular folder available on your Tivo. The data about the video that is displayed on your Tivo is sent by pytivo from a specially formatted metadata file for each video. The transfer program I use actually outputs one automatically so reading metadata from this significantly increased accuracy in Plex
* **Better segmentation** of movies and tv shows
  * Since my movies and tv shows aren't in different folders, they all reside in the same one because the transfer program doesn't know, this can detect which is which and places in the appropriate Plex library
  * I have a Movies and TV Shows library on my Plex server

## Use

I haven't made this for general use, but I thought it would be useful to release it for others to use as an example if they'd like to create their own Plex scanner. It's possible you can make use of it as-is.

To test out the scanner, you will need to download the project by either cloning the repo or downloading one of the release archives. 

On my Debian Linux machine, the Plex server was installed under `/var/lib/plexmediaserver/Library/Application Support/Plex Media Server`.

The `Scanners` folder from the project should be copied to the above folder (reflect your own Plex install location).

Restart the Plex media server so it picks up the new Scanners.

In the Plex web administration UI, you can configure Plex to use the new Scanners.

## License

Licensed under the GPLv2. Please see the LICENSE file for the complete license.
