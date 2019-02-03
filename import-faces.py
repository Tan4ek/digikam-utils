import argparse
import csv
from collections import namedtuple
from digikam_common import create_connection
from digikam_common import TagProperties
from digikam_common import Tag
from collections import defaultdict

CsvFace = namedtuple('Face', ['path', 'name', 'x', 'y', 'wight', 'height'])
ImagePathId = namedtuple('ImagePathId', ['id', 'path'])
JoinImageTagFace = namedtuple('JoinImageTagFace', ['imageid', 'path', 'tagid', 'csv_face', 'tag'])

ap = argparse.ArgumentParser()

ap.add_argument("-d", "--digikam-db-path", required=True,
                help="path to file digikam4.db. Example /home/user/images/digikam4.db")
ap.add_argument("--csv", required=True,
                help="path to csv with faces. header- 'path', 'name', 'x', 'y', 'wight', 'height'")
args = vars(ap.parse_args())


def read_faces(csv_path):
    def row_to_face(row):
        return CsvFace(row['path'], row['name'], row['x'], row['y'], row['wight'], row['height'])

    with open(csv_path, newline='') as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')
        return list(map(row_to_face, csv_reader))


def names(csv_faces):
    return set(map(lambda csv_face: csv_face.name, csv_faces))


def person_tag_properties(digikam_db_con):
    cursor = digikam_db_con.cursor()
    cursor.execute("""SELECT * FROM TagProperties WHERE property = 'person'""")
    return list(map(TagProperties._make, cursor.fetchall()))


def not_exists_names(digikam_names, csv_names):
    return csv_names.difference(digikam_names)


def create_tags_for_person(digikam_db_con, names_to_create):
    cursor = digikam_db_con.cursor()
    cursor.execute("SELECT MAX(id) AS max_id FROM Tags")
    first_element = cursor.fetchall()[0]
    max_id = first_element[0]
    insert_sql = "INSERT OR IGNORE INTO Tags (id, pid, name) VALUES (?, ?, ?)"
    for index, name_to_create in enumerate(names_to_create):
        cursor.execute(insert_sql, (max_id + index + 1, 23, name_to_create))
    digikam_db_con.commit()
    cursor.close()


def create_tag_properties_for_person(digikam_db_con, names_to_create):
    # акуратным будь возможно дублирование инсерта
    cursor = digikam_db_con.cursor()
    joined_names = ", ".join(map(lambda name: "'" + name + "'", names_to_create))
    cursor.execute("""INSERT INTO TagProperties (tagid, property, value)
                        SELECT id AS tagid, 'person' AS property, name AS value
                        FROM Tags WHERE value IN ({})""".format(joined_names))
    digikam_db_con.commit()
    cursor.close()


def select_image(digikam_db_con, csv_faces):
    cursor = digikam_db_con.cursor()
    csv_file_paths = {x.path for x in csv_faces}

    cursor.execute("""select
                     images.id         as image_id,
                     case albums.relativePath
                     when '/'
                       then album_root.specificPath || albums.relativePath || images.name
                     else album_root.specificPath || albums.relativePath || '/' || images.name
                     end               as file_path
                   from Images as images
                     join Albums as albums on images.album = albums.id
                     join AlbumRoots as album_root on album_root.id = albums.albumRoot;    
    """)
    return set(filter(lambda x: x.path in csv_file_paths, map(ImagePathId._make, cursor.fetchall())))


def select_tags(digikam_db_con, face_names):
    cursor = digikam_db_con.cursor()
    cursor.execute("""
    select tags.id as id, tags.pid as pid, tags.name as name, tags.icon as icon, tags.iconkde as iconkde
     from Tags as tags 
    join TagProperties as tag_properties
    on tag_properties.property = 'person'""")
    return list(filter(lambda x: x.name in face_names, map(Tag._make, cursor.fetchall())))


def join_csv_face_image_tag(csv_faces, tags, image_ids_paths):
    path_to_csv_face = defaultdict(list)
    for csv_face in csv_faces:
        path_to_csv_face[csv_face.path].append(csv_face)

    name_to_tag = {tag.name: tag for tag in tags}

    joined = []

    for (image_id, path) in image_ids_paths:
        for csv_face in path_to_csv_face[path]:
            tag = name_to_tag[csv_face.name]
            joined.append(JoinImageTagFace(image_id, path, tag.id, csv_face, tag))
    return joined


def insert_in_image_tags(digikam_db_con, joined):
    cursor = digikam_db_con.cursor()
    delete_image_tag_sql = "delete from ImageTags where imageid = ? and tagid = ?"
    insert_image_tag_sql = "insert into ImageTags (imageid, tagid) VALUES (?, ?)"
    delete_image_tag_property_sql = """delete from ImageTagProperties
     where imageid = ? and tagid = ? and property='tagRegion'"""
    insert_image_tag_property_sql = """insert into ImageTagProperties (imageid, tagid, property, value)
     VALUES (?, ?, 'tagRegion', ?)"""

    def image_tag_property_value(csv_face):
        return '<rect x="{}" y="{}" width="{}" height="{}"/>'.format(csv_face.x, csv_face.y,
                                                                     csv_face.wight, csv_face.height)

    for join in joined:
        cursor.execute(delete_image_tag_sql, (join.imageid, join.tagid))
        cursor.execute(insert_image_tag_sql, (join.imageid, join.tagid))
        cursor.execute(delete_image_tag_property_sql, (join.imageid, join.tagid))
        cursor.execute(insert_image_tag_property_sql,
                       (join.imageid, join.tagid, image_tag_property_value(join.csv_face)))
    digikam_db_con.commit()
    cursor.close()


def main(csv_path, digikam_db_path):
    with create_connection(digikam_db_path) as digikam_db_con:
        tag_properties = person_tag_properties(digikam_db_con)
        tag_names = set(map(lambda p: p.value, tag_properties))
        csv_faces = read_faces(csv_path)

        csv_names = names(csv_faces)

        names_to_create = not_exists_names(tag_names, csv_names)

        images_ids_paths = select_image(digikam_db_con, csv_faces)

        create_tags_for_person(digikam_db_con, names_to_create)
        create_tag_properties_for_person(digikam_db_con, names_to_create)

        tags = select_tags(digikam_db_con, csv_names)

        joined = join_csv_face_image_tag(csv_faces, tags, images_ids_paths)

        insert_in_image_tags(digikam_db_con, joined)


if __name__ == '__main__':
    main(args['csv'], args['digikam_db_path'])
