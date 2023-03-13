import json
import re
import sys

from pyparsing import lineno
import requests
import uuid
import time

import cv2
import numpy as np
import math
from operator import itemgetter

# 실수인지 확인하는 함수
def is_number(num):
    try:
        float(num)
        return True #num을 float으로 변환할 수 있는 경우
    except ValueError: #num을 float으로 변환할 수 없는 경우
        return False

class first:

    # 변수들 초기화 
    def __init__(self):
        
        # clova 설정
        self.api_url = '클로바 url 주소'
        self.secret_key = '클로바 secret 키'
        self.image_file = 'test.png'

        # 생성파일들
        self.output_file = 'output1.json'
        self.first_process_file='first_process.txt'
        self.infertext_file= 'inferText2.txt'
        self.nutritional_info='nutritional_info.txt'
        self.add_nutritional_info='add_nutritional_info.txt'
        self.add_nutritional_per='add_nutritional_per.txt'

        with open("first_process.txt",'w') as f:
            pass
        with open("inferText2.txt",'w') as f:
            pass

        # def process 변수들 
        self.Height = 50000 
        self.Width = 50000
        self.Throttle = 100
        self.x_min = self.Width
        self.x_max=0
        self.y_min = self.Height
        self.y_max=0
        self.s = []

        # 단위섭취량 보정계수
        self.multiple = 1
        self.total = 0
        self.sub = 0

        # 1일 권장섭취량(mg)
        self.recommended_salt=2000*7
        self.recommended_cholesterol=3000*7
        self.recommended_kcal=2000*7
        # 1일 권장섭취량(g)
        self.recommended_carbohydrate=130*7
        self.recommended_sugars=50*7
        self.recommended_fat=50*7
        self.recommended_transfat=2*7
        self.recommended_saturatedfat=15*7
        self.recommended_protein=60*7

        # error 넘버
        self.errornum = 0

    # naver clova ocr
    def clova(self):

        api_url = self.api_url
        secret_key = self.secret_key

        image_file = self.image_file
        output_file = self.output_file

        request_json = {
            'images': [
                {
                    'format': 'png',
                    'name': 'demo'
                }
            ],
            'requestId': str(uuid.uuid4()),
            'version': 'V2',
            'timestamp': int(round(time.time() * 1000))
        }

        payload = {'message': json.dumps(request_json).encode('UTF-8')}
        files = [
        ('file', open(image_file,'rb'))
        ]
        headers = {
        'X-OCR-SECRET': secret_key
        }

        response = requests.request("POST", api_url, headers=headers, data = payload, files = files)

        res = json.loads(response.text.encode('utf8'))
        #print(res)

        with open(output_file, 'w', encoding='utf-8') as outfile:
            json.dump(res, outfile, indent=4, ensure_ascii=False)

    # 크게 기울어진 사진 opencv 이용하여 평행하게 수정하기
    def level(self):
        # 기울어진 사진의 json파일
        output_file = self.output_file

        with open(output_file, 'r', encoding='utf-8') as f:
            json_object = json.load(f)

        level_target = ['나트륨', '탄수화물', '트랜스지방', '포화지방', '콜레스테롤', '단백질', '지방', 'kcal', 'g']

        horizontal = 0
        vertical = 0
        horizontal_sum = 0
        vertical_sum = 0
        level = 0
        level_sum = 0
        abs_count = 0

        for images in json_object['images']:

            for key in images['fields']:
                #print(key['inferText'])

                for target in level_target:

                    if key['inferText'] in target:

                        horizontal = (key['boundingPoly']['vertices'][1]["x"]-key['boundingPoly']['vertices'][0]["x"])
                        vertical = (key['boundingPoly']['vertices'][1]["y"]-key['boundingPoly']['vertices'][0]["y"])

                        horizontal_sum += horizontal
                        vertical_sum += vertical
                        if horizontal == 0:
                            continue
                        else:
                            level = vertical / horizontal
                            level_sum += level
                            abs_count = abs_count + 1
        
        if abs_count == 0:
            self.errornum=2
            return 0

        # print(abs_count)
        level = level_sum/abs_count
        # if horizontal_sum != 0:
        #     level = vertical_sum / horizontal_sum

        # 4.86도 이상 차이날 때
        # print (level)
        if abs(level) > 0.085:

            # 회전시킬 이미지
            srcimg = cv2.imread(self.image_file, cv2.IMREAD_COLOR)
        
            src_height, src_width, src_channel = srcimg.shape
            level_matrix = cv2.getRotationMatrix2D((src_width/2, src_height/2), np.arctan2(vertical_sum-100,horizontal_sum)*180/math.pi, 1)
            level_img = cv2.warpAffine(srcimg, level_matrix, (src_width, src_height))

            # 회전된 이미지파일
            cv2.imwrite('./level_image.png',level_img)
            print("회전")
            self.image_file = './level_image.png'
            start.clova()
        f.close()

    # naver clova ocr에서 잘못 인식한 영양성분 이름 수정하기
    def wrongocr(self):

        output_file = self.output_file

        with open(output_file, 'r', encoding='utf-8') as f:
            json_object_before = json.load(f)

        with open(output_file, 'w', encoding='utf-8') as mk_f:

            for images in json_object_before['images']:

                for key in images['fields']:

                    if ('탄수화무' in key['inferText'] or '탄수화믈' in key['inferText']    
                        or '탄수화몰' in key['inferText'] or '탄수와믈' in key['inferText'] 
                        or '탄수와몰' in key['inferText'] or '탄수와물' in key['inferText']
                        or '단수외울' in key['inferText']):
                        key['inferText'] = key['inferText'].replace(key['inferText'],'탄수화물')
                        # print(key['inferText'])

                    if ('나트륜' in key['inferText'] or '나트룸' in key['inferText']    
                        or '나트롬' in key['inferText'] or '나트름' in key['inferText'] 
                        or '다르륨' in key['inferText'] or '나르룸' in key['inferText']
                        or '트륨' in key['inferText']):
                        key['inferText'] = key['inferText'].replace(key['inferText'],'나트륨')
                        # print(key['inferText'])

                    if ('단백짐' in key['inferText'] or '단맥질' in key['inferText']    
                        or '단맥짐' in key['inferText'] or '딘백질' in key['inferText'] 
                        or '딘맥질' in key['inferText'] or '딘백짐' in key['inferText']):
                        key['inferText'] = key['inferText'].replace(key['inferText'],'단백질')
                        # print(key['inferText'])

                    if ('당루' in key['inferText'] or '당료' in key['inferText']    
                        or '당르' in key['inferText'] or '담류' in key['inferText'] 
                        or '담루' in key['inferText'] or '낭듀' in key['inferText']):
                        key['inferText'] = key['inferText'].replace(key['inferText'],'당류')
                        # print(key['inferText'])

                    if ('트랜스지망' in key['inferText'] or '트랜스자방' in key['inferText']    
                        or '트랜스지밤' in key['inferText'] or '트렌스지방' in key['inferText'] 
                        or '트렌스지밤' in key['inferText']):
                        key['inferText'] = key['inferText'].replace(key['inferText'],'트랜스지방')
                        # print(key['inferText'])

                    if ('포화지망' in key['inferText'] or '포화자방' in key['inferText']    
                        or '포화지밤' in key['inferText'] or '포하지방' in key['inferText'] 
                        or '포하지밤' in key['inferText'] or 'g미만|포화지방' in key['inferText']):
                        key['inferText'] = key['inferText'].replace(key['inferText'],'포화지방')
                        # print(key['inferText'])

                    if ('지망' in key['inferText'] or '자방' in key['inferText']    
                        or '지밤' in key['inferText'] or '자밤' in key['inferText'] 
                        or '지반' in key['inferText']):
                        key['inferText'] = key['inferText'].replace(key['inferText'],'지방')
                        # print(key['inferText'])

                    if ('콜레스테를' in key['inferText'] or '콜레스태롤' in key['inferText']    
                        or '콜래스테롤' in key['inferText'] or '콜래스테를' in key['inferText'] 
                        or '클레스테롤' in key['inferText']):
                        key['inferText'] = key['inferText'].replace(key['inferText'],'콜레스테롤')
                        # print(key['inferText'])
                    
                    if ('m' == key['inferText']):
                        key['inferText'] = key['inferText'].replace(key['inferText'],'mg')
                        # print(key['inferText'])

            json.dump(json_object_before,mk_f,indent='\t',ensure_ascii=False)

        f.close()
        mk_f.close()

    # 상품(식품) 유형 다음에 상품의 종류 써 있으므로
    # ocr에서 '유형' 다음으로 저장된 inferText 6개 정도를 저장한다
    def ingredient(self):

        output_file = 'output1.json'
        ingre_count = 0
        ingre_break = True

        with open(output_file, 'r', encoding='utf-8') as f:
            json_object = json.load(f)

        ingredient = []

        for images in json_object['images']:

            for key in images['fields']:

                if ingre_count >=1:
                    ingredient.append(key['inferText'])
                    ingre_count +=1
                if '유형' in key['inferText']:
                    ingredient.append(key['inferText'])
                    ingre_count = 1
                if ingre_count == 6:
                    ingre_break = False
                    break
                #print(ingre_count)
            if ingre_break == False:
                break

        #print(ingredient)
        f.close()
        self.ingredientlist = ingredient
    
    # ocr inferText를 읽고
    # ROI 설정 및 수직/수평인지 확인, 여러 예외처리 후
    # first_process.txt 파일에 줄 단위로 저장
    def process(self):

        output_file = self.output_file

        with open(output_file, 'r', encoding='utf-8') as f:
            json_object = json.load(f)

        sys.stdout=open(self.first_process_file,'w')

        for images in json_object['images']:
            for key in images['fields']:
                key['inferText'].replace(',' , '')


        # 필요 영양성분 이름 등을 확인하여 ROI 설정, 탐색 시간을 줄여줌
        for images in json_object['images']:

            for key in images['fields']:

                if ('탄수화물'  in key['inferText'] or
                    '단백질'    in key['inferText'] or
                    '지방'      in key['inferText'] or
                    '콜레스테롤' in key['inferText'] or
                    '당류'      in key['inferText'] or
                    '나트륨' in key['inferText'] or
                    '열량' in key['inferText'] or
                    'cal' in key['inferText'] or
                    '%' in key['inferText'] or
                    'g' in key['inferText'] or
                    '기준치' in key['inferText'] or
                    '영양성분' in key['inferText'] or
                    '영양정보' in key['inferText']):

                    if (key['boundingPoly']['vertices'][0]['x'] < self.x_min):
                        self.x_min = key['boundingPoly']['vertices'][0]['x'] - self.Throttle
                    if (key['boundingPoly']['vertices'][3]['x'] < self.x_min):
                        self.x_min = key['boundingPoly']['vertices'][3]['x'] - self.Throttle

                    if (key['boundingPoly']['vertices'][1]['x'] > self.x_max):
                        self.x_max = key['boundingPoly']['vertices'][1]['x'] + self.Throttle
                    if (key['boundingPoly']['vertices'][2]['x'] > self.x_max):
                        self.x_max = key['boundingPoly']['vertices'][2]['x'] + self.Throttle

                    if (key['boundingPoly']['vertices'][0]['y'] < self.y_min):
                        self.y_min = key['boundingPoly']['vertices'][0]['y'] - self.Throttle
                    if (key['boundingPoly']['vertices'][1]['y'] < self.y_min):
                        self.y_min = key['boundingPoly']['vertices'][1]['y'] - self.Throttle

                    if (key['boundingPoly']['vertices'][2]['y'] > self.y_max):
                        self.y_max = key['boundingPoly']['vertices'][2]['y'] + self.Throttle
                    if (key['boundingPoly']['vertices'][3]['y'] > self.y_max):
                        self.y_max = key['boundingPoly']['vertices'][3]['y'] + self.Throttle

        for images in json_object['images']:

            for key in images['fields']:

                if (key['boundingPoly']['vertices'][0]['x'] >= self.x_min and
                    key['boundingPoly']['vertices'][0]['y'] >= self.y_min and
                    key['boundingPoly']['vertices'][1]['x'] <= self.x_max and
                    key['boundingPoly']['vertices'][1]['y'] >= self.y_min and
                    key['boundingPoly']['vertices'][2]['x'] <= self.x_max and
                    key['boundingPoly']['vertices'][2]['y'] <= self.y_max and
                    key['boundingPoly']['vertices'][3]['x'] >= self.x_min and
                    key['boundingPoly']['vertices'][3]['y'] <= self.y_max):

                    self.s.append ([key['inferText'],
                        key['boundingPoly']['vertices'][0]['x'],
                        key['boundingPoly']['vertices'][0]['y'],
                        key['boundingPoly']['vertices'][1]['x'],
                        key['boundingPoly']['vertices'][1]['y'],
                        key['boundingPoly']['vertices'][2]['x'],
                        key['boundingPoly']['vertices'][2]['y'],
                        key['boundingPoly']['vertices'][3]['x'],
                        key['boundingPoly']['vertices'][3]['y']])

        # 수평인지 수직인지 확인, direction == 0 -> 수평 / direction == 1 -> 수직
        direction = 0
        difference = 500000
        closest_index = -1
    
        for i in range(len(self.s)):

            if re.search('나\s*트\s*륨\s*탄\s*수\s*화\s*물',self.s[i][0]):
                direction = 1
            
            if re.search('나\s*트\s*륨$',self.s[i][0]):
                for j in range(len(self.s)):

                    if  (((self.s[i][3] + self.s[i][5])/2 < (self.s[j][1]+self.s[j][3]+self.s[j][5]+self.s[j][7])/4) and
                        (self.s[i][4] <= (self.s[j][2]+self.s[j][8])/2 <= self.s[i][6])) :

                        if ((self.s[j][1]+self.s[j][3]+self.s[j][5]+self.s[j][7])/4 - (self.s[i][3] + self.s[i][5])/2) < difference:
                            difference = ((self.s[j][1]+self.s[j][3]+self.s[j][5]+self.s[j][7])/4 - (self.s[i][3] + self.s[i][5])/2)
                            closest_index = j

                if (closest_index != -1):
                    if re.search('^탄\s*수\s*화\s*물',self.s[closest_index][0]):
                        direction = 1
        
        # print(self.s)
        # ROI 내 전체 텍스트에 대해
        for text in self.s:
            # print(text)
            if text[0][0] == 'g' or (text[0][0] == 'm' and text[0][1] == 'g') or text[0][0] == 'x':
                center_x = (text[1] + text[3] + text[5] + text[7])/4
                left_y = (text[2] + text[8])/2

                # ROI 내 전체 텍스트에 대해
                closest_x = -1
                closest_index = -1

                for i in range(len(self.s)):
                    if ((self.s[i][3] + self.s[i][5])/2 < center_x and
                        (self.s[i][4] <= left_y <= self.s[i][6]) ):
   
                        if closest_x < (self.s[i][3] + self.s[i][5])/2 :
                            closest_x = (self.s[i][3] + self.s[i][5])/2
                            closest_index = i

                if closest_index != -1:

                    if (text[0][0] == 'g'):
                        self.s[closest_index][0]  = self.s[closest_index][0] + 'g'
                        text[0] = text[0][1:]




                    elif (text[0][0] == 'm' and text[0][1] == 'g'):
                        self.s[closest_index][0]  = self.s[closest_index][0] + 'mg'
                        text[0] = text[0][2:]

                    elif (text[0][0] == 'x'):
                        self.s[closest_index][0]  = self.s[closest_index][0] + text[0]
                        text[0] = text[0][len(text[0]):]

                    self.s[closest_index][2] = min(self.s[closest_index][2], 
                                            self.s[closest_index][4], 
                                            text[2], 
                                            text[4], )
                    self.s[closest_index][3] = max(self.s[closest_index][3], text[1])
                    self.s[closest_index][4] = self.s[closest_index][2]
                    self.s[closest_index][5] = max(self.s[closest_index][5], text[7])
                    self.s[closest_index][6] = max(self.s[closest_index][6], 
                                            self.s[closest_index][8], 
                                            text[6], 
                                            text[8], )
                    self.s[closest_index][8] = self.s[closest_index][6]

                    if len(text[0]) == 0:
                            for i in range(1,9):
                                text[i] = 0

        for text in self.s:
            if re.search('내\s*용\s*량',text[0]) :
                center_x = (text[1] + text[3] + text[5] + text[7])/4
                left_y = (text[2] + text[8])/2
                right_y = (text[4] + text[6])/2

                closest_x = -1
                closest_index = -1

                for i in range(len(self.s)):
                    if ((self.s[i][3] + self.s[i][5])/2 < center_x and
                        (self.s[i][4] <= left_y <= self.s[i][6]) ):
   
                        if closest_x < (self.s[i][3] + self.s[i][5])/2 :
                            closest_x = (self.s[i][3] + self.s[i][5])/2
                            closest_index = i

                if closest_index != -1:

                    if (len(text[0]) != 0 and len(self.s[closest_index][0]) != 0 and text[0][0] == '내' and self.s[closest_index][0][-1] == "총"):
                        text[0]  = "총" + text[0]
                        self.s[closest_index][0]  = self.s[closest_index][0][0:-1]

                        if len(self.s[closest_index][0]) == 0:
                            for i in range(1,9):
                                self.s[closest_index][i] = 0

                closest_x = -1
                closest_index = -1
                
                for i in range(len(self.s)):
                    if ((self.s[i][1] + self.s[i][3])/2 > center_x and
                        (self.s[i][1] <= right_y <= self.s[i][7]) ):
   
                        if closest_x > (self.s[i][1] + self.s[i][7])/2 :
                            closest_x = (self.s[i][1] + self.s[i][7])/2
                            closest_index = i

                if closest_index != -1:
                    # print("AAAAAAAAAAAAAAAAAAAAAAAA")

                    if (len(text[0]) != 0 and len(self.s[closest_index][0]) != 0 and text[0][-1] == '량' ):
                        text[0]  =  text[0] + self.s[closest_index][0]
                #         print("---------------------------------")

                #         # and re.search([0-9],self.s[closest_index][0][0])
                # else:
                #     print()



            if (len(text[0]) != 0) and (text[0][-1] == 'g'):
                closest_x = -1
                closest_index = -1
                
                for i in range(len(self.s)):
                    if ((self.s[i][1] + self.s[i][3])/2 > center_x and
                        (self.s[i][4] <= left_y <= self.s[i][6]) ):
   
                        if closest_x > (self.s[i][1] + self.s[i][7])/2 :
                            closest_x = (self.s[i][1] + self.s[i][7])/2
                            closest_index = i

                if closest_index != -1:

                    if len(self.s[closest_index][0]) != 0 and '당' == (self.s[closest_index][0][0]):
                        text[0]  = text[0] + '당'

                


                    
        print('direction임')
        print(direction)
        # print(self.s)
        # print("#########################")

        # ROI 내 전체 텍스트에 대해
        for text in self.s:

            # print(text[0])

            if ('탄수화물' in text[0] or '단백질' in text[0] or
                '지방' in text[0] or '당류' in text[0] or
                '포화지방' in text[0] or '트랜스지방' in text[0] or
                '나트륨' in text[0] or '콜레스테롤' in text[0]
                ):
            # if '탄수화물' in text[0]:

                center_x = (text[1] + text[3] + text[5] + text[7])/4
                center_y = (text[2] + text[4] + text[6] + text[8])/4

                horizon_index = []
                vertical_index = []
                tmp = []
                result = []

                # 수평: 영양성분 이름 기준 오른쪽 문자들을 self.s 리스트에 저장 후 내림차순 정리
                # 수직: 영양성분 이름 기준 아래쪽 문자들을 self.s 리스트에 저장 후 내림차순 정리
                if direction == 0:

                    for i in range(len(self.s)):
                        # if text[0] == '콜레스테롤':
                        #     print(self.s[i][0])
                        #     print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

                        # 사진의 굴곡으로 인해 center_y 계산 시 여유 +- 4를 둠
                        if ((self.s[i][1] + self.s[i][3] + self.s[i][5] + self.s[i][7])/4 > center_x and
                            (self.s[i][2]-4 <= center_y <= self.s[i][8]+4) ):
                            # print(self.s[i][0])
                            horizon_index.append(i)
                            tmp.append(self.s[i])
                    # 왼쪽 위 x 좌표 기준 배열 내림차순 정리
                    result=sorted(tmp,key=itemgetter(1))
                
                # if text[0] == '콜레스테롤':
                #     print(tmp)
                #     print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
                #     print(result)
                #     print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

                if direction == 1:

                    for i in range(len(self.s)):

                        if ((self.s[i][2] + self.s[i][4]+ self.s[i][6]+ self.s[i][8])/4 > center_y and
                            (self.s[i][1] <= center_x <= self.s[i][3]) ):
                            vertical_index.append(i)
                            tmp.append(self.s[i])
                    # 왼쪽 위 y 기준 배열 내림차순 정리
                    result=sorted(tmp,key=itemgetter(2))
                        
                difference = 50000
                closest_index = -1

                if direction == 0:

                    for i in range(len(horizon_index)):

                        if re.search('[0-9]\s*g',self.s[horizon_index[i]][0]) or re.search('[0-9]\s*mg',self.s[horizon_index[i]][0]):
                            closest_index = 1
                            break

                if direction == 1:

                    for i in range(len(vertical_index)):
                        #if re.search('[0-9]\s*g',s[vertical_index[i]][0]):
                        #if closest_index != -1:
                        #    break    
                        if re.search('[0-9]\s*g',self.s[vertical_index[i]][0]) or re.search('[0-9]\s*mg',self.s[vertical_index[i]][0]):
                            closest_index = 1
                            break
                
                # if text[0] == '단백질':
                # print("~~~~~~!!!!~~~~~~~~~")
                # print(text[0])
                # print(result)
                # print("~~~~~~~~~~~~~~~~~~~")
                # print(closest_index)

                # 내림차순 정리한 result 리스트 첫번째 인자에 g(mg)을 인식 후
                # 영양성분 이름에 붙여 파일에 출력
                # 첫번째 인자에 없을 시 두번째 인자에서 찾기
                if direction == 0:
                    if closest_index != -1:
                        if not "g" in text[0]:
                            if not "g" in result[0][0]:
                                if "mg" in result[1][0]:
                                    result[0][0] = result[0][0]+"mg"
                                    text[0] = text[0] + result[0][0]                         

                                elif "g" in result[1][0]:
                                    result[0][0] = result[0][0]+"g"
                                    text[0] = text[0] + result[0][0]

                                else:
                                    if ('콜레스테롤' in text[0] or '나트륨' in text[0]):
                                        result[0][0] = result[0][0]+"mg"
                                        text[0] = text[0] + result[0][0]
                                    else:
                                        result[0][0] = result[0][0]+"g"
                                        text[0] = text[0] + result[0][0]
                            
                            elif len(result) == 0:
                                if ('콜레스테롤' in text[0] or '나트륨' in text[0]):
                                    text[0] = text[0] + "mg"
                                else:
                                    text[0] = text[0] + "g"


                            else:
                                text[0] += result[0][0]

                if direction == 1:
                    if closest_index != -1:

                        for i in range(len(result)):

                            if "g" in result[i][0]:

                                text[0] = text[0] + result[i][0]

                                break

                if closest_index == -1:
                    if not result:
                        self.errornum = 1
                        continue
                    if ('콜레스테롤' in text[0] or '나트륨' in text[0]):
                        text[0] = text[0] + result[0][0] + "mg"
                    
                    else:
                        text[0] = text[0] + result[0][0] + "g"

        # for i in self.s:
        #     print(i[0])
        # print("@@@@@@@@@@@@@@@@@@@@@@@@@@")
        for i in self.s:
            # if '탄수화물' in i[0]:
            #     strings = i[0].split('탄')
            #     i[0] = '탄'+strings[1]
            # if '나트륨' in i[0]:
            #     strings = i[0].split('나')
            #     i[0] = '나'+strings[1]
            # if '당류' in i[0]:
            #     strings = i[0].split('당')
            #     i[0] = '당'+strings[1]
            # if '포화지방' in i[0]:
            #     strings = i[0].split('포')
            #     i[0] = '포'+strings[1]
            # if '트랜스지방' in i[0]:
            #     strings = i[0].split('트')
            #     i[0] = '트'+strings[1]
            # if '지방' in i[0]:
            #     strings = i[0].split('지')
            #     i[0] = '지'+strings[1]    
            # if '단백질' in i[0]:
            #     strings = i[0].split('단')
            #     i[0] = '단'+strings[1] 

            if ('나트륨' in i[0] and '탄수화물' in i[0]):
                strings = i[0].split('탄')
                strings1 = strings[0].split('나')
                print('나'+strings1[1])
                print('탄'+strings[1])
            elif ('탄수화물' in i[0] and '당류' in i[0]):
                strings = i[0].split('당')
                strings1 = strings[0].split('탄')
                print('탄'+strings1[1])
                print('당'+strings[1])
            # elif ('지방 ' in i[0] and '트랜스지방' in i[0] and '%' in i[0]):
            #     strings = i[0].split('트')
            #     strings1 = strings[0].split('지')
            #     print("~~~~~~~~~~~~")
            #     print(strings[0])
            #     print(strings1)
            #     print('지'+strings1[1])
            #     print('트'+strings[1])
            elif ('포화지방' in i[0] and '콜레스테롤' in i[0]):
                strings = i[0].split('콜')
                strings1 = strings[0].split('포')
                print('포'+strings1[1])
                print('콜'+strings[1])

            elif '탄수화물' in i[0]:
                strings = i[0].split('탄')
                i[0] = '탄'+strings[1]
                print(i[0])
            elif '나트륨' in i[0]:
                strings = i[0].split('나')
                i[0] = '나'+strings[1]
                print(i[0])
            elif '당류' in i[0]:
                strings = i[0].split('당')
                i[0] = '당'+strings[1]
                print(i[0])
            elif '포화지방' in i[0]:
                strings = i[0].split('포')
                i[0] = '포'+strings[1]
                print(i[0])
            elif '트랜스지방' in i[0]:
                strings = i[0].split('트')
                i[0] = '트'+strings[1]
                print(i[0])
            elif '지방' in i[0]:
                strings = i[0].split('지')
                i[0] = '지'+strings[1]  
                print(i[0])  
            elif '단백질' in i[0]:
                strings = i[0].split('단')
                i[0] = '단'+strings[1] 
                print(i[0])
            else:
                print(i[0])

        sys.stdout.close()

        f.close()
        
        # def process 결과 저장된 first_process.py 파일을 다시 읽고
        # 영양소에 g(mg)이 안붙어 있을 경우 끝에 g을 붙여준다. 예) 탄수화물11 (대부분 g일 때 인식을 못함)
        # first_process.py 파일에 추가한다.
        f1=open(self.first_process_file)
        data1=f1.readlines()

        sys.stdout=open(self.first_process_file,'a')
        print("~~~~~~~~~~~~~~~")
        for line in data1:

            if (re.search(r'지방\s*[0-9]',line)
                or re.search(r'나트륨[0-9]',line)
                or re.search(r'탄수화물[0-9]',line)
                or re.search(r'당류[0-9]',line)
                or re.search(r'콜레스테롤[0-9]',line)
                or re.search(r'단백질[0-9]',line)):

                # print("test")
                if not "g" in line:

                    line = line.strip() + "g"
                    print(line)

            # 숫자 뒤에 . 잘못 인식한 경우 예외 처리
            # 예) 탄수화물 25.g
            if re.search(r'[방+물+질+류]+[0-9]+.+g',line):
                # print(line)
                # print("~~~~~~~~~~~~~~~~~~~~~~~~~~")
                miss_g=re.search(r'[방+물+질+류](.+?)\s*g',line).group(1)
                if not miss_g.strip()[-1].isdigit():
                    line = re.search(r'(.+?)[0-9]',line).group(1)
                    # print('test1')
                    print(line.strip()+miss_g[:-1]+"g")
            elif re.search(r'[륨+롤]+[0-9]+.+g',line):
                # print(line)
                # print("~~~~~~~~~~~~~~~~~~~~~~~~~~")
                if re.search(r'[륨+롤]+[0-9]\s*mg',line):
                    # print('test2')
                    continue
                miss_mg=re.search(r'[륨+롤](.+?)\s*mg',line).group(1)
                if not miss_mg.strip()[-1].isdigit():
                    line = re.search(r'(.+?)[0-9]',line).group(1)
                    # print('test3')
                    print(line.strip()+miss_mg[:-1]+"mg")

                # bbb=re.search(r'[륨+롤](.+?)\s*g',line).group(1)
                # # print(aaa)
                # if not aaa.strip()[-1].isdigit():
                #     line = re.search(r'(.+?)[0-9]',line).group(1)
                #     print(line.strip()+aaa[:-1]+"mg")
                # elif 'g' in line:
                #     aaa=re.search(r'[방+륨+물+롤+질+류](.+?)\s*g',line).group(1)
                #     # print(aaa)
                #     if not aaa.strip()[-1].isdigit():
                #         line = re.search(r'(.+?)[0-9]',line).group(1)
                #         print(line.strip()+aaa[:-1]+"g")

        sys.stdout.close()

        f1.close()

    def extraction(self):

        f=open(self.first_process_file)
        data=f.readlines()

        sys.stdout=open(self.infertext_file,'w')

        for line in data:

            temp = 0

            if (re.search('1\s*회\s*제\s*공\s*량\s*당',line)):
                print('on')
                for line in data:
                    if (re.search('[0-9]+\s*회\s*제\s*공',line)):
                        temp = re.findall(r"(\d+)\s*회\s*제\s*공",line)
                        if self.multiple < int(temp[0]):
                            self.multiple = int(temp[0])
                            break
                break

            if (re.search('g\s*×\s*[0-9]',line)):
                temp = re.findall(r"g\s*×\s*(\d+)",line)
                self.multiple = int(temp[0])
                break

            if (re.search('총\s*내\s*용\s*량\s*(\d+)\s*g',line)):
                temp = re.findall(r"총\s*내\s*용\s*량\s*(\d+)\s*g",line)
                self.total = int(temp[0]) * 1000

            if (re.search('총\s*내\s*용\s*량\s*(\d+)\s*m\s*g',line)):
                temp = re.findall(r"총\s*내\s*용\s*량\s*(\d+)\s*m\s*g",line)
                self.total = int(temp[0])

            if (re.search(r"(\d+)\s*g\s*당",line)):
                temp = re.findall(r"(\d+)\s*g\s*당",line)
                self.sub = int(temp[0]) * 1000

            if (re.search(r"(\d+)\s*m\s*g\s*당",line)):
                temp = re.findall(r"(\d+)\s*m\s*g\s*당",line)
                self.sub = int(temp[0])

            if (self.total != 0 and self.sub != 0):
                self.multiple = self.total/self.sub
                break
            if (re.search('총\s*내\s*용\s*량\s*당',line)):
                self.multiple = 1
                break      

        f1=open(self.first_process_file)
        data1=f1.readlines()

        print('-영양성분- ',end=" ")

        for line in data1:
            if "나트륨" in line and "g" in line:
                nutrient="나트륨"
            elif "탄수화물" in line and "g" in line:
                nutrient="탄수화물"
            elif "당류" in line and "g" in line:
                nutrient="당류"
            elif "트랜스지방" in line and "g" in line:
                nutrient="트랜스지방"
            elif "포화지방" in line and "g" in line:
                nutrient="포화지방"
            elif "지방" in line and "g" in line:
                nutrient="지방"
            elif "콜레스테롤" in line and "g" in line:
                nutrient="콜레스테롤"
            elif "단백질" in line and "g" in line:
                nutrient="단백질"
            else:
                continue
            if re.search("[0-9]\s*mg",line):
                amount=re.search('{}(.+?)mg'.format(nutrient),line).group(1)
                if not is_number(amount):
                    continue
                else:
                    amount_num = float(amount)
                    print('!{}: {}mg'.format(nutrient,amount_num),end=" ")
            elif re.search("[0-9]\s*g",line):
                amount=re.search('{}(.+?)g'.format(nutrient),line).group(1)
                if not is_number(amount):
                    continue
                else:
                    amount_num = float(amount)
                    print('!{}: {}mg'.format(nutrient,amount_num*1000),end=" ")
            else:
                #에러삽입 (숫자누락 혹은 해석불가, 영양소:nutrient, 파일: json)
                #아래코드 삭제할것
                error_catch = -1


        print('끝',end="")

        print('\n\n총 영양성분은 위의',self.multiple,'배',end="")
        print('\n-총 영양성분- ',end="")

        for line in data1:
            if "나트륨" in line and "g" in line:
                nutrient="나트륨"
            elif "탄수화물" in line and "g" in line:
                nutrient="탄수화물"
            elif "당류" in line and "g" in line:
                nutrient="당류"
            elif "트랜스지방" in line and "g" in line:
                nutrient="트랜스지방"
            elif "포화지방" in line and "g" in line:
                nutrient="포화지방"
            elif "지방" in line and "g" in line:
                nutrient="지방"
            elif "콜레스테롤" in line and "g" in line:
                nutrient="콜레스테롤"
            elif "단백질" in line and "g" in line:
                nutrient="단백질"
            else:
                continue
            
            # 영양성분 g 사이 실수일때만 출력 예) 나트륨 베트남25g -> x
            if re.search("[0-9]\s*mg",line):
                amount=re.search('{}(.+?)mg'.format(nutrient),line).group(1)
                if not is_number(amount):
                    continue
                else:
                    amount_num = float(amount)
                    print('!{}: {}mg'.format(nutrient,amount_num*self.multiple),end=" ")
            elif re.search("[0-9]\s*g",line):
                amount=re.search('{}(.+?)g'.format(nutrient),line).group(1)
                if not is_number(amount):
                    continue
                else:
                    amount_num = float(amount)
                    print('!{}: {}g'.format(nutrient,amount_num*self.multiple),end=" ")
            else:
                #에러삽입 (숫자누락 혹은 해석불가, 영양소:nutrient, 파일: json)
                #아래코드 삭제할것
                error_catch = -1
                
        print('끝',end="")

        sys.stdout.close()
        f.close()

    def info(self):
        f=open(self.infertext_file)
        data=f.readlines()
        sys.stdout=open(self.nutritional_info,'a')

        protein_num = fat_num = carbohydrate_num = 0
        for line in data:
            if "-총 영양성분-" in line:
                # found=re.search('-총 영양성분- (.+?) 끝', line).group(1)
                # print(found,end=" ")

                if "!나트륨" in line:
                    found=re.search('!나트륨: (.+?)mg', line).group(1)
                    print('!나트륨          '+str(found)+' mg',end=" ")
                else:
                    print('!나트륨          0.0 mg',end=" ")
                if "!탄수화물" in line:
                    found=re.search('!탄수화물: (.+?)g', line).group(1)
                    print('!탄수화물       '+str(found)+' g',end=" ")
                else:
                    print('!탄수화물       0.0 g',end=" ")
                if "!당류" in line:
                    found=re.search('!당류: (.+?)g', line).group(1)
                    print('!당류              '+str(found)+' g',end=" ")
                else:
                    print('!당류              0.0 g',end=" ")
                if "!트랜스지방" in line:
                    found=re.search('!트랜스지방: (.+?)g', line).group(1)
                    print('!트랜스지방    '+str(found)+' g',end=" ")
                else:
                    print('!트랜스지방    0.0 g',end=" ")
                if "!포화지방" in line:
                    found=re.search('포화지방: (.+?)g', line).group(1)
                    print('!포화지방       '+str(found)+' g',end=" ")
                else:
                    print('!포화지방       0.0 g',end=" ")
                if "!지방" in line:
                    found=re.search('!지방: (.+?)g', line).group(1)
                    print('!지방              '+str(found)+' g',end=" ")
                else:
                    print('!지방              0.0 g',end=" ")
                if "!콜레스테롤" in line:
                    found=re.search('!콜레스테롤: (.+?)mg', line).group(1)
                    print('!콜레스테롤    '+str(found)+' mg',end=" ")
                else:
                    print('!콜레스테롤    0.0 mg',end=" ")
                if "!단백질" in line:
                    found=re.search('!단백질: (.+?)g', line).group(1)
                    print('!단백질           '+str(found)+' g',end=" ")
                else:
                    print('!단백질           0.0 g',end=" ")
            
                # 칼로리 계산
                if '!단백질' in line:
                    protein=re.search('!단백질: (.+?)g',line).group(1)
                    protein_num = float(protein)
                if '!지방' in line:
                    fat=re.search('!지방: (.+?)g',line).group(1)
                    fat_num = float(fat)
                if '!탄수화물' in line:
                    carbohydrate=re.search('!탄수화물: (.+?)g',line).group(1)
                    carbohydrate_num = float(carbohydrate)
                kcal = round(protein_num*4+fat_num*9+carbohydrate_num*4,1)
                print('칼로리           {} kcal'.format(kcal))

        sys.stdout.close()
        f.close()

    def add(self):
        f=open(self.nutritional_info)
        data=f.readlines()
        sys.stdout=open(self.add_nutritional_info,'w')

        #성분 mg 단위, 상품 번호에 따라 각각 표기
        salt=carbohydrate=sugars=fat=transfat=saturatedfat=cholesterol=protein=kcal=0
        count=0

        for line in data:
            count += 1
            if "!나트륨" in line:
                found=re.search('!나트륨          (.+?) mg', line).group(1)
                #print('나트륨'+str(count),str(found)+'mg',end=" ")
                salt_int=float(found)
                salt = salt+salt_int
            if "!탄수화물" in line:
                found=re.search('!탄수화물       (.+?) g', line).group(1)
                #print('탄수화물'+str(count),str(found)+'mg',end=" ")
                carbohydrate_int=float(found)
                carbohydrate = carbohydrate+carbohydrate_int
            if "!당류" in line:
                found=re.search('!당류              (.+?) g', line).group(1)
                #print('당류'+str(count),str(found)+'mg',end=" ")
                sugars_int=float(found)
                sugars = sugars+sugars_int
            if "!트랜스지방" in line:
                found=re.search('!트랜스지방    (.+?) g', line).group(1)
                #print('트랜스지방'+str(count),str(found)+'mg',end=" ")
                transfat_int=float(found)
                transfat = transfat+transfat_int
            if "!포화지방" in line:
                found=re.search('포화지방       (.+?) g', line).group(1)
                #print('포화지방'+str(count),str(found)+'mg',end=" ")
                saturatedfat_int=float(found)
                saturatedfat = saturatedfat+saturatedfat_int
            if "!지방" in line:
                found=re.search('!지방              (.+?) g', line).group(1)
                #print('지방'+str(count),str(found)+'mg',end=" ")
                fat_int=float(found)
                fat = fat+fat_int
            if "!콜레스테롤" in line:
                found=re.search('!콜레스테롤    (.+?) mg', line).group(1)
                #print('콜레스테롤'+str(count),str(found)+'mg',end=" ")
                cholesterol_int=float(found)
                cholesterol = cholesterol+cholesterol_int
            if "!단백질" in line:
                found=re.search('!단백질           (.+?) g', line).group(1)
                #print('단백질'+str(count),str(found)+'mg',end=" ")
                protein_int=float(found)
                protein = protein+protein_int
            if "칼로리" in line:
                found=re.search('칼로리           (.+?) kcal', line).group(1)
                #print('칼로리'+str(count),str(found)+'kcal',end=" ")
                kcal_int=float(found)
                kcal = kcal+kcal_int
            #print()
        kcal = round(kcal,1)
        #print()

        salt_per=carbohydrate_per=sugars_per=fat_per=transfat_per=saturatedfat_per=cholesterol_per=protein_per=kcal_per=0
        if salt != 0:
            salt_per=round(salt*100/self.recommended_salt)
        if carbohydrate != 0:    
            carbohydrate_per=round(carbohydrate*100/self.recommended_carbohydrate)
        if sugars != 0:
            sugars_per=round(sugars*100/self.recommended_sugars)
        if fat != 0:    
            fat_per=round(fat*100/self.recommended_fat)
        if transfat != 0:
            transfat_per=round(transfat*100/self.recommended_transfat)
        if saturatedfat != 0:
            saturatedfat_per=round(saturatedfat*100/self.recommended_saturatedfat)
        if cholesterol != 0:
            cholesterol_per=round(cholesterol*100/self.recommended_cholesterol)
        if protein != 0:
            protein_per=round(protein*100/self.recommended_protein)
        if kcal != 0:
            kcal_per=round(kcal*100/self.recommended_kcal)

        # 성분 총량 mg

        print('     <누적성분량>       <권장섭취량%(7일기준)>\n')
        print1 = '%-12s' % '나트륨'
        print2 = '%-22s' % '{} mg'.format(salt)
        print3 = '%-10s' % '{} %'.format(salt_per)
        print_tot1= print1+print2+print3
        print(print_tot1)
        print1 = '%-10s' % '탄수화물'
        print2 = '%-22s' % '{} mg'.format(round(carbohydrate,1))
        print3 = '%-10s' % '{} %'.format(carbohydrate_per)
        print_tot1= print1+print2+print3
        print(print_tot1)
        print1 = '%-15s' % '당류'
        print2 = '%-22s' % '{} mg'.format(round(sugars,1))
        print3 = '%-10s' % '{} %'.format(sugars_per)
        print_tot1= print1+print2+print3
        print(print_tot1)
        print1 = '%-15s' % '지방'
        print2 = '%-22s' % '{} mg'.format(round(fat,1))
        print3 = '%-10s' % '{} %'.format(fat_per)
        print_tot1= print1+print2+print3
        print(print_tot1)
        print1 = '%-8s' % '트랜스지방'
        print2 = '%-22s' % '{} mg'.format(round(transfat,1))
        print3 = '%-10s' % '{} %'.format(transfat_per)
        print_tot1= print1+print2+print3
        print(print_tot1)
        print1 = '%-10s' % '포화지방'
        print2 = '%-22s' % '{} mg'.format(round(saturatedfat,1))
        print3 = '%-10s' % '{} %'.format(saturatedfat_per)
        print_tot1= print1+print2+print3
        print(print_tot1)
        print1 = '%-8s' % '콜레스테롤'
        print2 = '%-22s' % '{} mg'.format(round(cholesterol,1))
        print3 = '%-10s' % '{} %'.format(cholesterol_per)
        print_tot1= print1+print2+print3
        print(print_tot1)
        print1 = '%-13s' % '단백질'
        print2 = '%-22s' % '{} mg'.format(round(protein,1))
        print3 = '%-10s' % '{} %'.format(protein_per)
        print_tot1= print1+print2+print3
        print(print_tot1)
        # 성분 총량 mg
        # print('     <누적성분량>      7일 기준\n')
        # print('나트륨          {} mg       {} %'.format(salt, salt_per))
        # print('탄수화물       {} g          {} %'.format(carbohydrate,carbohydrate_per))
        # print('당류              {} g         {} %'.format(sugars,sugars_per))
        # print('지방              {} g           {} %'.format(fat,fat_per))
        # print('트랜스지방     {} g           {} %'.format(transfat,transfat_per))
        # print('포화지방        {} g         {} %'.format(saturatedfat,saturatedfat_per))
        # print('콜레스테롤     {} mg       {} %'.format(cholesterol,cholesterol_per))
        # print('단백질           {} g           {} %'.format(protein,protein_per))
        # print('칼로리           {} kcal    {} %'.format(kcal,kcal_per))

        sys.stdout.close()

        # 성분 총량 1일 권장섭취량에 따른 % 계산

        # sys.stdout=open(self.add_nutritional_per,'w')

        # salt_per=carbohydrate_per=sugars_per=fat_per=transfat_per=saturatedfat_per=cholesterol_per=protein_per=kcal_per=0
        # if salt != 0:
        #     salt_per=round(salt*100/self.recommended_salt,1)
        # if carbohydrate != 0:    
        #     carbohydrate_per=round(carbohydrate*100/self.recommended_carbohydrate,1)
        # if sugars != 0:
        #     sugars_per=round(sugars*100/self.recommended_sugars,1)
        # if fat != 0:    
        #     fat_per=round(fat*100/self.recommended_fat,1)
        # if transfat != 0:
        #     transfat_per=round(transfat*100/self.recommended_transfat,1)
        # if saturatedfat != 0:
        #     saturatedfat_per=round(saturatedfat*100/self.recommended_saturatedfat,1)
        # if cholesterol != 0:
        #     cholesterol_per=round(cholesterol*100/self.recommended_cholesterol,1)
        # if protein != 0:
        #     protein_per=round(protein*100/self.recommended_protein,1)
        # if kcal != 0:
        #     kcal_per=round(kcal*100/self.recommended_kcal,1)

        # print('나트륨      {}%'.format(salt_per))
        # print('탄수화물    {}%'.format(carbohydrate_per))
        # print('당류        {}%'.format(sugars_per))
        # print('지방        {}%'.format(fat_per))
        # print('트랜스지방  {}%'.format(transfat_per))
        # print('포화지방    {}%'.format(saturatedfat_per))
        # print('콜레스테롤  {}%'.format(cholesterol_per))
        # print('단백질      {}%'.format(protein_per))
        # print('칼로리      {}%'.format(kcal_per))

        # sys.stdout.close()
        # f.close()

    def sub_nutri(self):
        # sys.stdout=open('./sub_nutri.txt','w')
        # nut_info=open('./nutritional_info.txt','r', encoding = "utf-8")
        # # nut_info.pop(2)
        # print(nut_info)
        # a=nut_info.readlines()[0:]
        # # b=nut_info.readlines()[2:4]
        # # c=a+b
        # # del a[1]
        # print(a)
        with open('nutritional_info.txt', 'r') as fin:
            data = fin.read().splitlines(True)
        with open('sub_nutri.txt', 'w') as fout:
            fout.writelines(data[0:1])
            fout.writelines(data[1:2])

        # self.nutri = nut_info.readlines()[1]

        # print(self.nutri)

        # self.total_nutrition = ""
        # fin = open('add_nutritional_info.txt','r')
        # data = fin.readlines()
        # for line in data:
        #     self.total_nutrition = self.total_nutrition + line
        # self.total_nutrition.replace('mg', 'mg\n')
        # self.total_nutrition.replace('g','g\n')
        # print(self.total_nutrition)
        # sys.stdout.close()
        # fin.close()
        # nut_info.close()

start=first()
start.__init__()

# 두개 같이 주석처리할것
# start.clova()
# start.level()

# start.wrongocr()
# start.ingredient()
# start.process()
# start.extraction()
# start.info()
# start.add()

# start.sub_nutri()