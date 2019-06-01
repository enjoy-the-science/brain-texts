import os
import nibabel as nib
import numpy as np
import cv2
from albumentations import (Compose, HorizontalFlip, VerticalFlip, ElasticTransform, GridDistortion, Resize, OneOf)


class NiiReader:
    def __init__(self, slice_size):
        self.height = slice_size[0]
        self.width  = slice_size[0]

        self.resize = Resize(height=self.height, width=self.width, interpolation=cv2.INTER_CUBIC)
        self.aug = Compose([
            HorizontalFlip(p=0.5),
            VerticalFlip(p=0.5),
            OneOf([
                ElasticTransform(p=0.5, alpha=120, sigma=120 * 0.05, alpha_affine=120 * 0.03),
                GridDistortion(p=0.5),
            ], p=0.5)
        ])

    @staticmethod
    def normalization_array(array):
        return (array / np.max(array) * 255).astype(np.uint8)

    @staticmethod
    def read_nii(path):
        img = nib.load(path)
        img = nib.as_closest_canonical(img)
        data = img.get_fdata()

        return NiiReader.normalization_array(data)

    @staticmethod
    def reshape(images):
        shape = (len(images), images[0].shape[0], images[0].shape[1], 1)
        images = np.array(images).astype(np.uint8)
        images.reshape(shape)

        return images

    def augmentation(self, orig, mask, count_aug):
        origs, masks = [orig], [mask]

        for i in range(count_aug):
            augmented = self.aug(image=orig, mask=mask)
            origs.append(augmented['image'])
            masks.append(augmented['mask'])

        return origs, masks

    def read_patient_nii(self, path_orig, path_mask, count_aug):
        orig, mask = NiiReader.read_nii(path_orig), NiiReader.read_nii(path_mask)

        origs, masks = [], []

        for i in range(orig.shape[2]):
            img, img_mask = orig[:, :, i], mask[:, :, i]
            resized = self.resize(image=img, mask=img_mask)

            orig_aug, mask_aug = self.augmentation(resized['image'], resized['mask'], count_aug)
            origs += orig_aug
            masks += mask_aug

        return NiiReader.reshape(origs), NiiReader.reshape(masks)

    def save_to_npy(self, path_to_save, patient_id, path_orig, path_mask, count_aug):
        orig, mask = self.read_patient_nii(path_orig, path_mask, count_aug)

        patient_path = os.path.join(path_to_save, patient_id)
        os.makedirs(patient_path, exist_ok=True)

        for i in range(len(orig)):
            np.save(os.path.join(patient_path, "IM%s" % i), np.array([orig[i], mask[i]]))
            # np.save(os.path.join(patient_path, "M%s.npy"), orig)
