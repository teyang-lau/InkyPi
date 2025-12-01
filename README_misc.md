
### Copy images from pi to local
```
scp -r teyang@ty-inky.local:~/InkyPi/outputs/ai_images "C:\Users\Te Yang Lau\Downloads"

scp -r teyang@ty-inky.local:~/InkyPi/outputs/ai_images "/Users/teyang_lau/Downloads"

scp -r "/Users/teyang_lau/Downloads/safari" teyang@ty-inky.local:~/InkyPi/playlist_images/safari 
```

```
# image folder
/home/teyang/InkyPi/playlist_images/InkyAIImages
```

### get ip address of pi
```
hostname -I
```

### local dev
```
python src/inkypi.py --dev
```

```
nmcli connection show
sudo nmcli connection down preconfigured
```