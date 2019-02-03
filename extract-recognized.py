#!/usr/bin/python

import xml.etree.ElementTree as ET
import subprocess
import pathlib
import argparse
from digikam_common import create_connection

ap = argparse.ArgumentParser()
ap.add_argument("-d", "--digikamdb-path", required=True,
                help="path to file digikam4.db. Example /home/user/images/digikam4.db")
ap.add_argument("-o", "--out-path", type=str, required=True,
                help="recognised faces output path. Example /home/user/recognised_faces")
args = vars(ap.parse_args())


def select_tag_ids_user_names(conn):
    cur = conn.cursor()
    cur.execute("SELECT id as tag_id, name as user_name from Tags where pid=23 ")

    rows = cur.fetchall()
    cur.close()
    return rows


def select_image_tag_properties(conn):
    cur = conn.cursor()
    cur.execute("""select
                     images.id         as image_id,
                     iprop.value       as prop_value,
                     case albums.relativePath
                     when '/'
                       then album_root.specificPath || albums.relativePath || images.name
                     else album_root.specificPath || albums.relativePath || '/' || images.name
                     end               as file_path,
                     images.name       as file_name,
                     images.uniqueHash as file_uniq_hash,
                     tags.name as name,
                     images.filesize   as file_size
                   from ImageTagProperties as iprop
                     join Images as images on iprop.imageid = images.id
                     join Albums as albums on images.album = albums.id
                     join AlbumRoots as album_root on album_root.id = albums.albumRoot
                     join Tags as tags on tags.id = iprop.tagid
                   where tags.pid = 23;""")
    image_tag_properties = cur.fetchall()
    cur.close()
    return image_tag_properties


def extract(digikam4_db_path, out_path):
    digikam4_db_conn = create_connection(digikam4_db_path)
    with digikam4_db_conn:
        print("Query for tagid and user")
        tag_ids_users = select_tag_ids_user_names(digikam4_db_conn)

        print("Creating output folders")
        for tag_id_user in tag_ids_users:
            pathlib.Path(out_path + "/" + tag_id_user[1]).mkdir(parents=True, exist_ok=True)

        images = select_image_tag_properties(digikam4_db_conn)
        for image in images:
            recognise_props = ET.fromstring('<' + image[1].split('<', 1)[1]).attrib
            file_path = image[2]
            file_name = image[3]
            file_uniq_hash = image[4]
            crop_param = "{width}x{height}+{x}+{y}".format(width=recognise_props["width"],
                                                           height=recognise_props["height"],
                                                           x=recognise_props["x"],
                                                           y=recognise_props["y"])
            image_path = "{out_path}/{user_name}/{hash}_{file_name}".format(out_path=out_path,
                                                                            user_name=image[5],
                                                                            hash=file_uniq_hash,
                                                                            file_name=file_name)
            subprocess_param = ["convert", file_path, "-crop", crop_param, "+repage", image_path]
            print("call convert command" + str(subprocess_param))
            subprocess.run(subprocess_param)


if __name__ == '__main__':
    extract(args["digikamdb_path"], args["out_path"])
