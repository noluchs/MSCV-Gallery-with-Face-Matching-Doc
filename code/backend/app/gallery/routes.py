from app.gallery import bp
from flask import Blueprint, request, jsonify, current_app
from app.models import Gallery
from app.schemas import GallerySchema
from app.extensions import db
import logging
import uuid
import os
import boto3

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('S3_KEY'),
    aws_secret_access_key=os.getenv('S3_SECRET'),
    region_name=os.getenv('S3_REGION_2')
)


@bp.route('/', methods=['GET'])
def get_galleries():
    galleries = Gallery.query.all()
    galleries_data = []
    for gallery in galleries:
        gallery_data = GallerySchema().dump(gallery)
        if gallery.cover_image_url:
            gallery_data['cover_image_url'] = f"https://{current_app.config['S3_BUCKET_2']}.s3.{current_app.config['S3_REGION_2']}.amazonaws.com/{gallery.cover_image_url}"
        galleries_data.append(gallery_data)
    return jsonify(galleries_data)

@bp.route('/', methods=['POST'])
def create_gallery():
    logging.debug("Received create gallery request")

    name = request.form.get('name')
    cover_image = request.files.get('cover_image')

    logging.debug(f"Gallery name: {name}")
    logging.debug(f"Cover image: {cover_image}")

    if not name:
        logging.error("Name is required")
        return jsonify({'error': 'Name is required'}), 400

    cover_image_filename = None
    if cover_image:
        # Generate a unique filename using uuid.uuid4()
        file_extension = cover_image.filename.split('.')[-1]  # Get the original file extension
        filename = f"{uuid.uuid4()}.{file_extension}"
        try:
            s3_client.upload_fileobj(
                cover_image,
                current_app.config['S3_BUCKET_2'],
                filename
            )
            cover_image_filename = filename  # Only save the filename in the database
            logging.debug(f"Uploaded cover image to S3: {cover_image_filename}")
        except Exception as e:
            logging.error(f"Failed to upload cover image to S3: {e}")
            return jsonify({'error': 'Failed to upload cover image'}), 500

    gallery = Gallery(name=name, cover_image_url=cover_image_filename)
    try:
        db.session.add(gallery)
        db.session.commit()
        logging.debug(f"Created gallery: {gallery.id}")
    except Exception as e:
        logging.error(f"Failed to create gallery: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create gallery'}), 500

    return jsonify(GallerySchema().dump(gallery)), 201

@bp.route('/<int:id>', methods=['DELETE'])
def delete_gallery(id):
    gallery = Gallery.query.get_or_404(id)
    db.session.delete(gallery)
    db.session.commit()

    return jsonify({'message': 'Gallery deleted successfully'}), 200