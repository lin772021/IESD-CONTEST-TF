import csv, os
import numpy as np
import tensorflow as tf
from random import shuffle
from sklearn.model_selection import KFold
from scipy.fftpack import fft


def myfft(x):
    fft_x = fft(x)                                            #  fft计算
    amp_x = abs(fft_x)/len(x)*2                                 # 纵坐标变换
    label_x = np.linspace(0,int(len(x)/2)-1,int(len(x)/2))    # 生成频率坐标
    # amp = amp_x[0:int(len(x)/2)]                              # 选取前半段计算结果即可
    # amp[0] = 0                                              # 可选择是否去除直流量信号
    fs = 250                                                  # 采样率250hz
    fre = label_x/len(x)*fs                                   # 频率坐标变换
    # pha = np.unwrap(np.angle(fft_x))                          # 计算相位角并去除2pi跃变
    return amp_x


def ACC(mylist):
    tp, fn, fp, tn = mylist[0], mylist[1], mylist[2], mylist[3]
    total = sum(mylist)
    acc = (tp + tn) / total
    return acc


def PPV(mylist):
    tp, fn, fp, tn = mylist[0], mylist[1], mylist[2], mylist[3]
    # for the case: there is no VA segs for the patient, then ppv should be 1
    if tp + fn == 0:
        ppv = 1
    # for the case: there is some VA segs, but the predictions are wrong
    elif tp + fp == 0 and tp + fn != 0:
        ppv = 0
    else:
        ppv = tp / (tp + fp)
    return ppv


def NPV(mylist):
    tp, fn, fp, tn = mylist[0], mylist[1], mylist[2], mylist[3]
    # for the case: there is no non-VA segs for the patient, then npv should be 1
    if tn + fp == 0:
        npv = 1
    # for the case: there is some VA segs, but the predictions are wrong
    elif tn + fn == 0 and tn + fp != 0:
        npv = 0
    else:
        npv = tn / (tn + fn)
    return npv


def Sensitivity(mylist):
    tp, fn, fp, tn = mylist[0], mylist[1], mylist[2], mylist[3]
    # for the case: there is no VA segs for the patient, then sen should be 1
    if tp + fn == 0:
        sensitivity = 1
    else:
        sensitivity = tp / (tp + fn)
    return sensitivity


def Specificity(mylist):
    tp, fn, fp, tn = mylist[0], mylist[1], mylist[2], mylist[3]
    # for the case: there is no non-VA segs for the patient, then spe should be 1
    if tn + fp == 0:
        specificity = 1
    else:
        specificity = tn / (tn + fp)
    return specificity


def BAC(mylist):
    sensitivity = Sensitivity(mylist)
    specificity = Specificity(mylist)
    b_acc = (sensitivity + specificity) / 2
    return b_acc


def F1(mylist):
    precision = PPV(mylist)
    recall = Sensitivity(mylist)
    if precision + recall == 0:
        f1 = 0
    else:
        f1 = 2 * (precision * recall) / (precision + recall)
    return f1


def FB(mylist, beta=2):
    precision = PPV(mylist)
    recall = Sensitivity(mylist)
    if precision + recall == 0:
        f1 = 0
    else:
        f1 = (1+beta**2) * (precision * recall) / ((beta**2)*precision + recall)
    return f1


def stats_report(mylist):
    f1 = round(F1(mylist), 5)
    fb = round(FB(mylist), 5)
    se = round(Sensitivity(mylist), 5)
    sp = round(Specificity(mylist), 5)
    bac = round(BAC(mylist), 5)
    acc = round(ACC(mylist), 5)
    ppv = round(PPV(mylist), 5)
    npv = round(NPV(mylist), 5)

    output = str(mylist) + '\n' + \
             "F-1 = " + str(f1) + '\n' + \
             "F-B = " + str(fb) + '\n' + \
             "SEN = " + str(se) + '\n' + \
             "SPE = " + str(sp) + '\n' + \
             "BAC = " + str(bac) + '\n' + \
             "ACC = " + str(acc) + '\n' + \
             "PPV = " + str(ppv) + '\n' + \
             "NPV = " + str(npv) + '\n'

    print("F-1 = ", F1(mylist))
    print("F-B = ", FB(mylist))
    print("SEN = ", Sensitivity(mylist))
    print("SPE = ", Specificity(mylist))
    print("BAC = ", BAC(mylist))
    print("ACC = ", ACC(mylist))
    print("PPV = ", PPV(mylist))
    print("NPV = ", NPV(mylist))

    return output


def loadCSV(csvf):
    dictLabels = {}
    with open(csvf, 'r') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        next(csvreader)  # 跳过头部
        for row in csvreader:
            filename = row[0]
            label = row[1]
            if label in dictLabels:
                dictLabels[label].append(filename)
            else:
                dictLabels[label] = [filename]
    return dictLabels


def txt_to_numpy(filename, row):
    file = open(filename)
    lines = file.readlines()
    datamat = np.arange(row, dtype=np.floating)
    row_count = 0
    for line in lines:
        line = line.strip().split(' ')
        datamat[row_count] = line[0]
        row_count += 1
    return datamat


class ToTensor(object):
    def __call__(self, sample):
        text, label = sample['ECG_seg'], sample['label']
        text = tf.convert_to_tensor(text, dtype=tf.float32)  # 转换为 TensorFlow tensor
        return {'ECG_seg': text, 'label': label}


class ECG_DataSET():
    def __init__(self, root_dir, indice_dir, mode, size, subject_id=None, transform=None):
        self.root_dir = root_dir
        self.indice_dir = indice_dir
        self.size = size
        self.names_list = []
        self.transform = transform

        csvdata_all = loadCSV(os.path.join(self.indice_dir, mode + '_indice.csv'))

        for i, (k, v) in enumerate(csvdata_all.items()):
            full_path = os.path.join(root_dir, k)
            # Check if the subject ID matches
            if subject_id is not None and k.startswith(subject_id):
                self.names_list.extend([(full_path, int(v[0]))])
                # print()
            elif subject_id is None:
                self.names_list.append((full_path, int(v[0])))
                # print()
        if subject_id is None:
            shuffle(self.names_list)
        # print()

    def __len__(self):
        return len(self.names_list)

    def __getitem__(self, idx):
        filepath, label = self.names_list[idx]
        if not os.path.isfile(filepath):
            print(f'{filepath} does not exist')
            return None

        data = np.loadtxt(filepath).astype(np.float32)
        # FFT
        # data = myfft(data)
        # 归一化
        # data = (data - data.min()) / (data.max() - data.min())
        # 标准化
        # data = (data - data.mean()) / data.std()
        data = data.reshape(-1, 1, 1)

        if self.transform:
            data = self.transform({'ECG_seg': data, 'label': label})
        return data


def create_dataset(data_cls, batch_size):
    def gen():
        for sample in data_cls:
            yield sample['ECG_seg'], sample['label']

    return tf.data.Dataset.from_generator(
        gen,
        output_types=(tf.float32, tf.int64),
        output_shapes=((1250, 1, 1), ())
    ).batch(batch_size).prefetch(tf.data.experimental.AUTOTUNE)


def classify_indice(src):
    ''' 
    根据标签类别分类写入.csv文件，用于重新划分训练集和验证集
    通过classify_indice('train_indice.csv')调用
    '''
    with open(f'./data_indices/{src}', 'r', encoding='utf-8') as file:
        # 逐行读取文件
        for line in file:
            if len(line.split('-')) < 2: # 跳过第一行
                continue
            label = line.split('-')[1]
            filename = f'./data_indices/{label}_indice.csv'
            
            with open(filename, 'a', encoding='utf-8') as file:
                if os.path.getsize(filename) == 0:
                    file.write('label,Filename\n')
                file.write(line)
    return


class ECG_DataSET_kfold():
    def __init__(self, root_dir, indice_dir, mode, size, subject_id=None, transform=None):
        self.root_dir = root_dir
        self.indice_dir = indice_dir
        self.size = size
        self.names_list = []
        self.transform = transform
        self.fold_count = 10  # 默认10折交叉验证

        csvdata_all = loadCSV(os.path.join(self.indice_dir, mode + '_indice.csv'))

        for i, (k, v) in enumerate(csvdata_all.items()):
            full_path = os.path.join(root_dir, k)
            # Check if the subject ID matches
            if subject_id is not None and k.startswith(subject_id):
                self.names_list.extend([(full_path, int(v[0]))])
                # print()
            elif subject_id is None:
                self.names_list.append((full_path, int(v[0])))
                # print()
        if subject_id is None:
            shuffle(self.names_list) # shuffle the dataset
        # print()
        self.kfold = KFold(n_splits=self.fold_count)
        self.fold_indices = list(self.kfold.split([x[0] for x in self.names_list], [x[1] for x in self.names_list]))

    def __len__(self):
        return len(self.names_list)

    def __getitem__(self, idx):
        filepath, label = self.names_list[idx]
        if not os.path.isfile(filepath):
            print(f'{filepath} does not exist')
            return None

        data = np.loadtxt(filepath).astype(np.float32).reshape(-1, 1, 1)  # 调整reshape，确保维度正确
        if self.transform:
            data = self.transform({'ECG_seg': data, 'label': label})
        return data


def create_dataset_kfold(data_cls, batch_size, fold_index):
    train_index, val_index = fold_index
    train_data = [data_cls[i] for i in train_index]
    val_data = [data_cls[i] for i in val_index]
    
    def gen(dataset):
        for sample in dataset:
            yield sample['ECG_seg'], sample['label']

    train_dataset = tf.data.Dataset.from_generator(
        lambda:gen(train_data),
        output_types=(tf.float32, tf.int64),
        output_shapes=((1250, 1, 1), ())
    ).batch(batch_size).prefetch(tf.data.experimental.AUTOTUNE)

    val_dataset = tf.data.Dataset.from_generator(
        lambda:gen(val_data),
        output_types=(tf.float32, tf.int64),
        output_shapes=((1250, 1, 1), ())
    ).batch(batch_size).prefetch(tf.data.experimental.AUTOTUNE)

    return train_dataset, val_dataset