# Extracting ResNet101 features for images

import torch
import torchvision.models as models
import torchvision.transforms as transforms
from torch.autograd import Variable
from PIL import Image
import os
import numpy as np
import scipy.io as sio

# Load the pretrained model - ResNet101
model = models.resnet101(pretrained=True)

# Use the model object to select the desired layer
layer = model._modules.get('avgpool')
print(layer)

# Set model to evaluation mode
model.eval()

# Image transforms
# scaler = transforms.Resize((224, 224))
# normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
# to_tensor = transforms.ToTensor()

preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def get_vector(image_name):

    my_embedding = torch.zeros(1, 2048, 1, 1)

    try:
        # 1. Load the image with Pillow library
        img = Image.open(image_name)
        img = img.convert('RGB')
        # 2. Create a PyTorch Variable with the transformed image
        t_img = preprocess(img).unsqueeze(0)
        # t_img = Variable(normalize(to_tensor(scaler(img))).unsqueeze(0))
        # 3. Create a vector of zeros that will hold our feature vector
        #    The 'avgpool' layer has an output size of 512 (resnet18)  2048 for resnet101
        # my_embedding = torch.zeros(1, 2048, 1, 1)

        # 4. Define a function that will copy the output of a layer
        def copy_data(m, i, o):
            my_embedding.copy_(o.data)

        # 5. Attach that function to our selected layer
        h = layer.register_forward_hook(copy_data)
        # 6. Run the model on our transformed image
        model(t_img)
        # 7. Detach our copy function from the layer
        h.remove()

    except Exception:
        print('Invalid Image !')

    # 8. Return the feature vector
    return my_embedding.numpy()


if __name__ == "__main__":

    data_root = '/Volumes/Kellan/datasets/data_KG_GNN_GCN'
    image_data_root = os.path.join(data_root, 'ucf101_images_400')
    #image_data_root = os.path.join(data_root, 'hmdb51_images_400')
    dataset = 'ucf101'

    if os.path.exists(os.path.join(image_data_root, '.DS_Store')):
        os.remove(os.path.join(image_data_root, '.DS_Store'))
    else:
        # get all folder names as action classes
        all_classes = os.listdir(image_data_root)
        avg_action_embedding = np.empty((2048, 0))

        for action in all_classes:
            action_path = os.path.join(image_data_root, action)
            if os.path.exists(os.path.join(action_path, '.DS_Store')):
                # remove non-image file
                os.remove(os.path.join(action_path, '.DS_Store'))
            else:
                all_images_each_class = os.listdir(action_path)
                all_images_embedding = np.empty((0, 2048, 1, 1))

            for image in all_images_each_class:
                image_path = os.path.join(action_path, image)
                #print(image_path)
                image_feature = get_vector(image_path)
                # put all image features into one numpy array
                all_images_embedding = np.vstack((all_images_embedding, image_feature))
                print("all_images_embedding", all_images_embedding.shape)

            # reshpe to (2048, number of images) number of images with 2048 dimension for each action class
            all_images_embedding_reshape = all_images_embedding.reshape(all_images_embedding.shape[1],
                                                                        all_images_embedding.shape[0])

            # TODO: Save each image representation for each action class
            # TODO: Save all images Reps. in mat file cell(1 * number of class), cell as: 400*2048, 398*2048, .....
            sio.savemat(os.path.join(data_root, dataset + '_img_resnet101_features', dataset + '_' + action + '_all_img_resnet101.mat'),
                        {'all_img_resnet101': all_images_embedding_reshape})

            # (2048, number of images)
            print("all_images_embedding_reshape", all_images_embedding_reshape.shape)

            # TODO: Averaging image Rep. from mat file for each cell/action class
            # TODO: Save averagered image Rep. to one file Size(2048, number of classes)
            # TODO: Option - consider different approaches to combine image Rep.

            # Averaing image features for each class
            avg_image_embedding = np.mean(all_images_embedding_reshape, axis=1).reshape(2048, 1)
            print("avg_image_embedding.shape", avg_image_embedding.shape) # (2048, 1)
            print(avg_image_embedding)

            # put all action embedding together
            # (2048, number of classes)
            avg_action_embedding = np.hstack((avg_action_embedding, avg_image_embedding))
            print("avg_action_embedding", avg_action_embedding.shape)

            # Save data
            sio.savemat(os.path.join(data_root, dataset + '_avg_img_resnet101.mat'),
                        {'avg_img_resnet101': avg_action_embedding})

    '''
    image_path = './ucf101_images/Surfing/95.8.jpg'
    image_feature = get_vector(image_path)
    print(image_feature)
    print(image_feature.shape)
    '''