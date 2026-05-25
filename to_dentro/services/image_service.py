import cloudinary.uploader
from typing import Optional

def upload_image(file, folder: str = "to-dentro-app") -> Optional[str]:
    """
    Uploads an image file to Cloudinary and returns its secure URL.
    :param file: The file-like object to upload.
    :param folder: The Cloudinary folder to store the image in.
    :return: The secure URL of the uploaded image, or None if it failed.
    """

    if not file:
        return None

    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="image"
        )
        return result.get("secure_url")
    except Exception as e:
        print(f"Error uploading image to Cloudinary: {e}")
        return None

def delete_image(public_id: str) -> bool:
    """
    Deletes an image from Cloudinary by its public ID.
    :param public_id: The public ID of the image to delete.
    :return: True if successfully deleted, False otherwise.
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        print(f"Error deleting image from Cloudinary: {e}")
        return False

def delete_image_by_url(url: str) -> bool:
    """
    Deletes an image from Cloudinary by extracting its public ID from the URL.
    :param url: The secure URL of the image.
    :return: True if successfully deleted, False otherwise.
    """
    if not url:
        return False
    try:
        parts = url.split("/image/upload/")
        if len(parts) < 2:
            return False
        path = parts[1]
        path_parts = path.split("/")
        if path_parts[0].startswith("v") and path_parts[0][1:].isdigit():
            path_parts = path_parts[1:]
        
        public_id_with_ext = "/".join(path_parts)
        public_id = public_id_with_ext.rsplit(".", 1)[0]
        
        return delete_image(public_id)
    except Exception as e:
        print(f"Error parsing public ID or deleting image by url: {e}")
        return False

