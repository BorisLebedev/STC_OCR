import fitz
import re
from os import listdir
from os import rename
from os import path
import cv2
import pytesseract
import sqlite3
import numpy as np
from PIL import Image

def connect_db(db_name):
    global conn
    global c
    conn = sqlite3.connect(db_name)
    conn.execute('PRAGMA foreign_keys = 1')
    c = conn.cursor()
    with conn:
        c.execute("""SELECT name, deno FROM  product""")
    product = {}
    for name, deno in c.fetchall():
        product[deno] = name
    return product

def convert_file(file, zoom):
    doc = fitz.open(file)
    page = doc.load_page(0)
    page.set_rotation(270)
    mat = fitz.Matrix(zoom, zoom)

    pix = page.get_pixmap(matrix=mat)
    pix.save(temp_image)

def crop_img(img, crop):
    h = img.shape[0]
    w = img.shape[1]
    h1 = int(h//crop[0])  # kd950   td950   t1300   4.57
    h2 = int(h//crop[1])  # kd1250  td1250  t1540   3.86
    w1 = int(w//crop[2])  # kd4100  td6900  t3230   2.60
    w2 = int(w//crop[3])  # kd5800  td8200  t8200   1.07
    # img = img[h1:h2, w1:w2]
    # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # ret, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    # img_erode = cv2.erode(thresh, np.ones((10, 10), np.uint8), iterations=10)
    # contours, hierarchy = cv2.findContours(img_erode, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    # cv2.drawContours(img, contours, len(contours) - 1, (0, 255, 0), 3)
    # cv2.imwrite("img.png", img)
    # (x, y, w, h) = cv2.boundingRect(contours[-1])
    # return img[y:y+h, x:x+w]
    return img[h1:h2, w1:w2]

def tess_text(img, img_type='КД'):
    # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # ret, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    # img = cv2.erode(thresh, np.ones((1, 1), np.uint8), iterations=1)
    # cv2.imwrite("tt_temp_2.png", img)
    text = pytesseract.image_to_string(img, lang='rus')
    text = text.replace('\n', '')
    text = text.replace('\f', '')
    text = text.replace('"', '')
    text = text.replace('$', '8')
    text = text.replace('|', '')
    text = text.lstrip()
    text = text.rstrip()
    if img_type == 'ТЕКСТ':
        cv2.imwrite("text.png", img)
    return get_deno(text, img_type)

def get_deno(text, img_type='КД'):
    deno_dev = r'[А-Я]{4}'
    deno_code = r'\.[0-9]{6}\.[0-9]{3}'
    deno_code_spo = r'\.[0-9]{5}-[0-9]{2}'
    deno_code_td = r'\.[0-9]{5}\.[0-9]{5}'
    deno_var = r'-[0-9]{2,3}'
    deno_text = r'[А-Я-0-9]*'
    deno_r = f'{deno_dev}{deno_code}{deno_var}'
    deno_r_00 = f'{deno_dev}{deno_code_spo}{deno_var}'
    deno_r_soft = f'{deno_dev}{deno_code}'

    if img_type == 'КД':
        reg_exp = f'{deno_r_00}|{deno_r}|{deno_r_soft}'
        text = re.search(reg_exp, text).group(0)
    elif img_type == 'ТД':
        reg_exp = f'{deno_dev}{deno_code_td}'
        text = re.search(reg_exp, text).group(0)
    elif img_type == 'ТЕКСТ':
        pass
    else:
        pass
    return text

def rename_and_save(directory, file, directory_result, name, try_num=0):
    if try_num != 0:
        try_name = f' КОПИЯ {try_num}.pdf'
    else:
        try_name = f'.pdf'

    try:
        rename(path.join(directory, file), path.join(directory_result, name + try_name))
    except FileExistsError:
        try_num += 1
        rename_and_save(directory=directory,
                        directory_result=directory_result,
                        name=name,
                        file=file,
                        try_num=try_num)

def convert():
    for file in listdir(directory):
        if file != '.gitkeep':
            try:
                convert_file(file=path.join(directory, file),
                             zoom=10)
                img = cv2.imread(temp_image)
                img_kd = crop_img(img=img,
                                  crop=kd_crop)
                cv2.imwrite("kd_temp.png", img_kd)

                img_td = crop_img(img=img,
                                  crop=td_crop)
                cv2.imwrite("td_temp.png", img_td)

                img_tt = crop_img(img=img,
                                  crop=tt_crop)
                cv2.imwrite("tt_temp.png", img_tt)

                kd_deno = tess_text(img=img_kd, img_type='КД')
                td_deno = tess_text(img=img_td, img_type='ТД')
                if kd_deno in product:
                    td_name = product[kd_deno]
                else:
                    try:
                        td_name = tess_text(img=img_tt, img_type='ТЕКСТ')
                    except:
                        td_name = 'НЕИЗВЕСТНО'
                name = f'{kd_deno} ({td_deno}) {td_name}'
                name = name.replace('/', ' . ')
                name = name.replace('"', '')
                rename_and_save(directory=directory,
                                directory_result=directory_result,
                                file=file,
                                name=name)
            except AttributeError:
                pass
            except FileNotFoundError:
                rename_and_save(directory=directory,
                                directory_result=directory_result,
                                file=file,
                                name='')
            except RuntimeError:
                convert()


if __name__ == '__main__':
    product = connect_db('DB.db')
    directory = 'scan'
    directory_result = 'documents'
    temp_image = "temp.png"
    pytesseract.pytesseract.tesseract_cmd = r'C:\Users\boiu.lebedev\AppData\Local\Tesseract-OCR\tesseract.exe'
    kd_crop = (6.25, 4.06, 2.05, 1.45)  #(6.25, 4.76, 2.05, 1.45)
    td_crop = (6.25, 4.06, 1.22, 1.03)  #(6.25, 4.76, 1.22, 1.03)
    tt_crop = (4.5, 3.67, 2.55, 1.18)   #(4.5, 3.97, 2.55, 1.18)
    convert()