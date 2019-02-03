## extract-recognized.py

Comparable with [digiKam 5.9](https://www.digikam.org/news/2018-03-25-5.9.0_release_announcement/)

Depends on [imageMagick convert](https://imagemagick.org/script/convert.php)

Usage
```bash
python3 extract-recognized.py -d /home/user/images/digikam4.db -o /home/user/recognized_faces
```

## import-faces.py

Comparable with [digiKam 5.9](https://www.digikam.org/news/2018-03-25-5.9.0_release_announcement/)

This util would be helpful when you want to import face which had been recognised by custom utils (like [face_recognision](https://github.com/ageitgey/face_recognition) library or other).
Faces imports from csv file:

```csv
path,name,x,y,wight,height
/home/user/Photos/under_water.jpg,SpongeBob SquarePants,3950,1383,322,322
/home/user/Photos/sky.jpg,Donald Duck,3534,872,666,667
```
**path** - absolute path to image. The image have to exist in Album, if not, face tag willn't import to digiKam

**name** - this will be [a face tag](https://docs.kde.org/trunk5/en/extragear-graphics/digikam/using-facetagging.html) in digiKam.

**x, y, wight, height** - coordinates of a face

Usage
```bash
python3 import-faces.py --digikam-db-path /home/user/images/digikam4.db --csv /home/user/recognized_faces.csv
```
