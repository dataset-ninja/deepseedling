# https://figshare.com/s/616956f8633c17ceae9b

import csv
import os
import shutil
from collections import defaultdict
from urllib.parse import unquote, urlparse

import numpy as np
import supervisely as sly
from dotenv import load_dotenv
from supervisely.io.fs import (
    dir_exists,
    file_exists,
    get_file_ext,
    get_file_name,
    get_file_name_with_ext,
    get_file_size,
)
from supervisely.io.json import load_json_file
from tqdm import tqdm

import src.settings as s
from dataset_tools.convert import unpack_if_archive


def download_dataset(teamfiles_dir: str) -> str:
    """Use it for large datasets to convert them on the instance"""
    api = sly.Api.from_env()
    team_id = sly.env.team_id()
    storage_dir = sly.app.get_data_dir()

    if isinstance(s.DOWNLOAD_ORIGINAL_URL, str):
        parsed_url = urlparse(s.DOWNLOAD_ORIGINAL_URL)
        file_name_with_ext = os.path.basename(parsed_url.path)
        file_name_with_ext = unquote(file_name_with_ext)

        sly.logger.info(f"Start unpacking archive '{file_name_with_ext}'...")
        local_path = os.path.join(storage_dir, file_name_with_ext)
        teamfiles_path = os.path.join(teamfiles_dir, file_name_with_ext)

        fsize = api.file.get_directory_size(team_id, teamfiles_dir)
        with tqdm(desc=f"Downloading '{file_name_with_ext}' to buffer...", total=fsize) as pbar:
            api.file.download(team_id, teamfiles_path, local_path, progress_cb=pbar)
        dataset_path = unpack_if_archive(local_path)

    if isinstance(s.DOWNLOAD_ORIGINAL_URL, dict):
        for file_name_with_ext, url in s.DOWNLOAD_ORIGINAL_URL.items():
            local_path = os.path.join(storage_dir, file_name_with_ext)
            teamfiles_path = os.path.join(teamfiles_dir, file_name_with_ext)

            if not os.path.exists(get_file_name(local_path)):
                fsize = api.file.get_directory_size(team_id, teamfiles_dir)
                with tqdm(
                    desc=f"Downloading '{file_name_with_ext}' to buffer...",
                    total=fsize,
                    unit="B",
                    unit_scale=True,
                ) as pbar:
                    api.file.download(team_id, teamfiles_path, local_path, progress_cb=pbar)

                sly.logger.info(f"Start unpacking archive '{file_name_with_ext}'...")
                unpack_if_archive(local_path)
            else:
                sly.logger.info(
                    f"Archive '{file_name_with_ext}' was already unpacked to '{os.path.join(storage_dir, get_file_name(file_name_with_ext))}'. Skipping..."
                )

        dataset_path = storage_dir
    return dataset_path


def count_files(path, extension):
    count = 0
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(extension):
                count += 1
    return count


def convert_and_upload_supervisely_project(
    api: sly.Api, workspace_id: int, project_name: str
) -> sly.ProjectInfo:
    # project_name = "figshare"
    dataset_path = "/mnt/d/datasetninja-raw/deepseedling/7940456"
    batch_size = 30
    anns_ext = ".json"

    def create_ann(image_path):
        labels = []
        tags = []

        if ds_name == "UGA2018":
            tag_value = get_file_name(image_path)[:6]
            tag = sly.Tag(tag_meta, value=tag_value)
            tags.append(tag)

        if ds_name == "UGA2015":
            tag_value = image_path.split("/")[-2]
            tag = sly.Tag(tag_meta, value=tag_value)
            tags.append(tag)

        image_np = sly.imaging.image.read(image_path)[:, :, 0]
        img_height = image_np.shape[0]
        img_wight = image_np.shape[1]

        bboxes_data = image_to_bboxes[get_file_name_with_ext(image_path)]
        x_reshape = reshape_data[ds_name][0]
        y_reshape = reshape_data[ds_name][1]

        for bboxes in bboxes_data:
            left = int(bboxes["x1"] * x_reshape)
            right = int(bboxes["x2"] * x_reshape)
            top = int(bboxes["y1"] * y_reshape)
            bottom = int(bboxes["y2"] * y_reshape)
            rectangle = sly.Rectangle(top=top, left=left, bottom=bottom, right=right)

            obj_class = name_to_class[bboxes["tags"][0]]

            label = sly.Label(rectangle, obj_class)
            labels.append(label)

        return sly.Annotation(img_size=(img_height, img_wight), labels=labels, img_tags=tags)

    obj_class_plant = sly.ObjClass("plant", sly.Rectangle)
    obj_class_weed = sly.ObjClass("weed", sly.Rectangle)

    tag_meta = sly.TagMeta("id", sly.TagValueType.ANY_STRING)

    name_to_class = {"Plant": obj_class_plant, "Weed": obj_class_weed}

    project = api.project.create(workspace_id, project_name, change_name_if_conflict=True)
    meta = sly.ProjectMeta(obj_classes=[obj_class_plant, obj_class_weed], tag_metas=[tag_meta])
    api.project.update_meta(project.id, meta.to_json())

    reshape_data = {
        "UGA2018": (1.32, 1.32),
        "TAMU2015": (1, 1),
        "UGA2015": (1.68, 1.68),
    }

    for ds_name in os.listdir(dataset_path):
        ds_path = os.path.join(dataset_path, ds_name)
        if dir_exists(ds_path):
            dataset = api.dataset.create(project.id, ds_name, change_name_if_conflict=True)

            for subfolder in os.listdir(ds_path):
                image_to_bboxes = defaultdict(list)
                images_path = os.path.join(ds_path, subfolder)
                if dir_exists(images_path):
                    ann_path = os.path.join(ds_path, subfolder + anns_ext)
                    anns_data = load_json_file(ann_path)["frames"]

                    images_names = [
                        im_name
                        for im_name in os.listdir(images_path)
                        if get_file_ext(im_name) != ".db"
                    ]
                    images_names = sorted(images_names)

                    for idx, im_name in enumerate(images_names):
                        if subfolder == "117" and idx == 0:
                            idx += 1
                        curr_im_bboxes = anns_data.get(str(idx), [])
                        image_to_bboxes[im_name] = curr_im_bboxes

                    progress = sly.Progress("Create dataset {}".format(ds_name), len(images_names))

                    for images_names_batch in sly.batched(images_names, batch_size=batch_size):
                        images_pathes_batch = [
                            os.path.join(images_path, im_name) for im_name in images_names_batch
                        ]

                        if ds_name == "UGA2015":
                            new_images_names = [
                                get_file_name(im_name) + "_" + subfolder + get_file_ext(im_name)
                                for im_name in images_names_batch
                            ]
                            images_names_batch = new_images_names

                        img_infos = api.image.upload_paths(
                            dataset.id, images_names_batch, images_pathes_batch
                        )
                        img_ids = [im_info.id for im_info in img_infos]

                        anns = [create_ann(image_path) for image_path in images_pathes_batch]
                        api.annotation.upload_anns(img_ids, anns)

                        progress.iters_done_report(len(images_names_batch))
    return project
