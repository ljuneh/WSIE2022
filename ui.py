from re import U
import re
import os
import shutil
import json
import urllib.request
import random
import cv2
from enum import auto
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import uic
import numpy as np
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import pyzbar.pyzbar as pyzbar
import time
import datetime
import calendar
import copy
from final import first

cap = cv2.VideoCapture(0)

cred = credentials.Certificate('./key.json')
firebase_admin.initialize_app(cred,{
    'databaseURL' : 'https://signfiftyoneman-default-rtdb.asia-southeast1.firebasedatabase.app/' 
    #'databaseURL' : '데이터 베이스 url'
})
cnt = 0

#기존의 코드는 스레드 클래스와 메인 클래스간에 parent를 추가해 스레드에서 메인에 있는 위젯을 편집함
#해당 코드는 기존의 코드와 다르게 스레드에서는 위젯 편집을 하지 않고 영상 처리에 필요한 작업만 하고
#메인 클레스에 정보를 전송함    위젯 편집이나 라벨에 출력하는 것들은 다 메인에서 처리하고 이후 구현해야할 다른 기능들도 모두 메인에 작성하면 됨
#로그인 시 사용되는 스레드, 웹캠의 이미지 데이터와 이미지를 통해 해석한 qr코드를 메인 클레스에 전송한다
Thread_running = True
class Thread(QThread):
    transimage = pyqtSignal(np.ndarray)
    transuid = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.pre = None
        self.now = None
        self.uid = None
    def run(self):
        global Thread_running
        global cap
        
        while Thread_running:
            ret, frame = cap.read()


            if ret:
                decodedObjects = pyzbar.decode(frame)
                self.display(frame, decodedObjects)
                for obj in (decodedObjects):
                    self.uid = (obj.data.decode("utf-8"))
                rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.transimage.emit(rgbImage)
                self.now = self.uid
                if self.now != self.pre:
                    self.transuid.emit(self.now)
                    
                self.pre = self.uid
                
        # cap.release()
        self.pre = None
        self.now = None
        self.uid = None
        # print("Thread end")

    

    def display(self, im, decodedObjects):
        for decodedObject in decodedObjects:
            points = decodedObject.polygon

            if len(points) > 4: 
                hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32)) 
                hull = list(map(tuple, np.squeeze(hull))) 
            else: 
                hull = points

            n = len(hull)

            for j in range(0, n): 
                cv2.line(im, hull[j], hull[(j + 1) % n], (255, 0, 0), 3) 

    def stop(self):
        
        global Thread_running
        Thread_running = False
        self.quit()
        self.wait(1000)
        # print("Thread stoped")

    def pause(self):
        
        global Thread_running
        Thread_running = False
        self.wait(1000)
        # print("Thread pause")

    def resume(self):
        
        global Thread_running
        Thread_running = True
        self.wait(1000)
        # print("Thread resume")

#상품을 찍는데 사용되는 스레드
Thread2_running = True
class Thread2(QThread):
    transimage = pyqtSignal(np.ndarray)
    

    def __init__(self):
        super().__init__()
        
    def run(self):
        global Thread2_running
        global cap
        
        while Thread2_running:
            ret, frame = cap.read()
            if ret:

                black = np.zeros((frame.shape[0], frame.shape[1], 3), np.uint8)
                black1 = cv2.rectangle(black, (160, 80), (480, 400), (255, 255, 255), -1)
                gray = cv2.cvtColor(black, cv2.COLOR_BGR2GRAY)
                ret, b_mask = cv2.threshold(gray, 127, 255, 0)
                fin = cv2.bitwise_and(frame, black1)

                hsv = cv2.cvtColor(fin, cv2.COLOR_BGR2HSV)

                l_h = 0
                l_s = 11
                l_v = 21
                u_h = 72
                u_s = 255
                u_v = 255

                lower = np.array([l_h, l_s, l_v])
                upper = np.array([u_h, u_s, u_v])

                mask = cv2.inRange(hsv, lower, upper)
                kernel = np.ones((3, 3), np.uint8)
                # canny = cv2.Canny(mask, 127, 255)
                # mask = cv2.erode(mask, kernel)

                # Contours detection
                if int(cv2.__version__[0]) > 3:
                    # Opencv 4.x.x
                    contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_TC89_KCOS)
                else:
                    # Opencv 3.x.x
                    _, contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_TC89_KCOS)

                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
                    x = approx.ravel()[0]
                    y = approx.ravel()[1]

                    if area > 5000:
                        cv2.drawContours(frame, [approx], 0, (0, 0, 255), 5)

                self.transimage.emit(frame)
                
        # cap.release()
        # print("Thread2 end")


    def stop(self):
        global Thread2_running
        Thread2_running = False
        self.quit()
        self.wait(1000)
        # print("Thread2 stoped")

    def pause(self):
        global Thread2_running
        Thread2_running = False
        self.wait(1000)
        # print("Thread2 pause")

    def resume(self):
        global Thread2_running
        Thread2_running = True
        self.wait(1000)
        # print("Thread2 resume")

formClass = uic.loadUiType("./UI.ui")[0]

class Ui(QMainWindow, formClass):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.uid = None
        self.image = None
        self.ref = db.reference('List of Users')
        self.th = Thread()
        self.th.transimage.connect(self.logincam)
        self.th.transuid.connect(self.finduid)
        self.th2 = Thread2()
        self.th2.transimage.connect(self.capcam)


        self.Buyitem = []
        self.BuyitemNum = 0
        self.now = -1
        self.abc = first(0,0)
        self.nutri = ""
        self.total_nutrition = ""
        self.Fileclear()
        self.allergy = ""
        self.allergywarning = 0
        self.ingrelist = []
        self.Addingrelist()
        self.Buyitemingrelist = []
        self.recommend = ""
        self.Onemorepicture = False
        self.recommendingredient = ""
        self.recommendurl = ""
        self.recommendstep = ""
        self.recommendpicurl = ""
        self.data = []
        self.data_2 = []
        self.EachEuclidean = None
        self.diabetes = None
        self.max_diabetes = 99999
        self.hyperlipidemia = None
        self.max_hyperlipidemia = 99999
        self.obesity = None
        self.max_obesity = 99999
        self.hypertension = None
        self.max_hypertension = 99999




        self.initUI()
        self.buttonSetting()



    def Addingrelist(self):
        file123 = open('./ingredientlist.txt', 'r', encoding="utf-8")
        lines = file123.readlines()
        for line in lines:
            if line == '\n':
                lines.remove(line)
                
        for item in lines:
            self.ingrelist.append(item.strip('\n'))
        file123.close()

    def Fileclear(self):
        fi = open('./nutritional_info.txt','w')
        fi.write(" ")
        fi.close()

    def euclidean(self,list_1,list_2):
        sum_of = 0
        for i in range(2,len(list_1)-1):
            sum_of += (float(list_1[i]) - float(list_2[i]))**2
        sum_of **= 0.5
        return sum_of





    def buttonSetting(self):
        self.pushButton.clicked.connect(self.Capture)
        self.pushButton_3.clicked.connect(self.StackedPage)
        self.pushButton_7.clicked.connect(self.Logout)

        
        self.pushButton.clicked.connect(self.ProductPage)
        self.pushButton_4.clicked.connect(self.PhotoPage)
        
        self.pushButton_9.clicked.connect(self.StackedPage)
        self.pushButton_2.clicked.connect(self.Additem)
        self.pushButton_6.clicked.connect(self.PhotoPage)
        
        self.pushButton_10.clicked.connect(self.Next)
        self.pushButton_11.clicked.connect(self.Before)
        self.pushButton_12.clicked.connect(self.Deleteitem)
        self.pushButton_5.clicked.connect(self.Recommend)
        self.pushButton_14.clicked.connect(self.StackedPage)
        # self.pushButton_15.clicked.connect(self.Search)
        # self.pushButton_8.clicked.connect(self.SearchResult)

    @pyqtSlot(str)
    def finduid(self, uid):
        self.uid = uid
        # print(self.uid)
        if self.uid in self.ref.get():
            # print("key exist")
            
            ref2 = self.ref.child(self.uid)
            
            self.th.pause()

            with open("./first_process.txt",'w') as f:
                    pass
            with open("./inferText2.txt",'w') as f:
                pass
            with open("./nutritional_info.txt",'w') as f:
                pass
            with open("./add_nutritional_info.txt",'w') as f:
                pass
            with open("./add_nutritional_per.txt",'w') as f:
                pass

            self.allergy = ref2.get()['allergy']

            if ref2.get()['record'] == '0':
                # print('hi\n\n\n')
                ref2.child('record').set({
                    'record': ''
                })    
                record_ref = ref2.child('record')
                record_ref.update({
                        'month0': 0,
                        'day0': 0, 
                })    
                
                for i in range (12):
                    record_ref.update({
                        i+1:''
                    })    
                    record_ref.child(str(i+1)).update({
                        'natryum':0,
                        'tansu':0,
                        'dangryu':0,
                        'transzibang':0,
                        'powhazibang':0,
                        'zibang':0,
                        'cholesterol':0,
                        'danbaek':0,
                        'kcal':0,
                        'days':0
                    })
            else:
                pass

            # print(self.allergy)


            self.stackedWidget.setCurrentIndex(1)

        else:
            # print("key not exist")
            errorMsg = '로그인 실패'
            QMessageBox.about(self,"실패",errorMsg)

        # self.th.exit()

    


    @pyqtSlot(np.ndarray)
    def logincam(self, image):
        
        h, w, ch = image.shape
        bytesPerLine = ch * w
        convertToQtFormat = QImage(image.data, w, h, bytesPerLine, QImage.Format_RGB888)
        
        p = convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
        self.label.setPixmap(QPixmap.fromImage(p))
        

    @pyqtSlot(np.ndarray)
    def capcam(self, image):
        self.image = copy.deepcopy(image)
        rgbImage = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgbImage.shape
        bytesPerLine = ch * w
        convertToQtFormat = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
        
        p = convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
        self.label_3.setPixmap(QPixmap.fromImage(p))

    def initUI(self):

        self.stackedWidget.setCurrentIndex(6)
        self.qPixmapFileVar = QPixmap()
        self.qPixmapFileVar.load("start_image.jpg")
        self.qPixmapFileVar = self.qPixmapFileVar.scaledToWidth(600)
        self.label_15.setPixmap(self.qPixmapFileVar)
        self.pushButton_13.clicked.connect(self.loginstart)

    def loginstart(self):
        self.stackedWidget.setCurrentIndex(0)
        
        self.th.start()
        self.th2.start()

    def Capture(self):

        # 사용자 키, 몸무게... 따라 칼로리 설정
        ######################################
        ref = db.reference('List of Users')
        users_ref = ref.child(self.uid)
        height = float(users_ref.get()['height'])
        weight = float(users_ref.get()['weight'])
        age = float(users_ref.get()['password'])
        neurologic = users_ref.get()['neurologic']
        gender = users_ref.get()['gender']
        if gender == "남자":
            if neurologic == "비활동적":
                PA = 1.1
            elif neurologic == "약간 활동적":
                PA = 1.24
            elif neurologic == "활동적":
                PA = 1.36
            elif neurologic == "매우 활동적":
                PA = 1.48
            EEE = 622 - 9.53 * age + PA * (15.91 * weight + 5.366 * height)
        elif gender == "여자":
            if neurologic == "비활동적":
                PA = 1.2
            elif neurologic == "약간 활동적":
                PA = 1.29
            elif neurologic == "활동적":
                PA = 1.37
            elif neurologic == "매우 활동적":
                PA = 1.45
            EEE = 354 - 6.91 * age + PA * (9.36 * weight + 7.26 * height)
        # print(EEE)
        ###################################################

        #캡쳐부분 더 추가할거 있으면 여기에 하면 됨
        if self.image is not None and not self.Onemorepicture:

            cv2.imwrite('./test.png', self.image)
            self.abc.__init__(EEE,height)
            self.abc.clova()
            self.abc.level()
            self.abc.wrongocr()
            self.abc.process()
            self.abc.extraction()
            self.abc.info()
            allergy = self.DetectAllergy()
            for item in allergy:
                if item in self.allergy:
                    self.AllergyWarning()
                    break

        elif self.image is not None and self.Onemorepicture :
            cv2.imwrite('./test.png', self.image)
            self.abc.__init__(EEE,height)
            self.abc.clova()
            self.abc.level()
            self.abc.ingredient()
            allergy = self.DetectAllergy()
            for item in allergy:
                if item in self.allergy:
                    self.AllergyWarning()
                    break

    def Logout(self):
        
        self.th.resume()
        self.th.start()

        fin = open('./add_nutritional_info.txt','r')
        data=fin.readlines()
        users_ref = self.ref.child(self.uid)
        today = datetime.date.today()
        div = 7

        for line in data:
            if "나트륨" in line and "g" in line:
                nutrient="natryum"
                nutrient_name="나트륨"
            elif "탄수화물" in line and "g" in line:
                nutrient="tansu"
                nutrient_name="탄수화물"
            elif "당류" in line and "g" in line:
                nutrient="dangryu"
                nutrient_name="당류"
            elif "트랜스지방" in line and "g" in line:
                nutrient="transzibang"
                nutrient_name="트랜스지방"
            elif "포화지방" in line and "g" in line:
                nutrient="powhazibang"
                nutrient_name="포화지방"
            elif "지방" in line and "g" in line:
                nutrient="zibang"
                nutrient_name="지방"
            elif "콜레스테롤" in line and "g" in line:
                nutrient="cholesterol"
                nutrient_name="콜레스테롤"
            elif "단백질" in line and "g" in line:
                nutrient="danbaek"
                nutrient_name="단백질"
            elif "칼로리" in line and "kcal" in line:
                nutrient="kcal"
                nutrient_name="칼로리"    
            else:
                continue

            if re.search("[0-9]\s*mg",line):
                amount=re.search('{}(.+?)mg'.format(nutrient_name),line).group(1)
                amount_num = float(amount)
                # print('!{}: {}mg'.format(nutrient,amount_num*self.multiple),end=" ")
            elif re.search("[0-9]\s*g",line):
                amount=re.search('{}(.+?)g'.format(nutrient_name),line).group(1)
                amount_num = float(amount)
            elif re.search("[0-9]\s*kcal",line):
                amount=re.search('{}(.+?)kcal'.format(nutrient_name),line).group(1)
                amount_num = float(amount)    
                # print('!{}: {}g'.format(nutrient,amount_num*self.multiple),end=" ")
            else:
                #에러삽입 (숫자누락 혹은 해석불가, 영양소:nutrient, 파일: json)
                #아래코드 삭제할것
                error_catch = -1

            # 월별 영양성분량 누적
            ##############################
            record_ref = users_ref.child('record')
            month_ref = record_ref.child(str(today.month))
            amount_num2 = float(month_ref.get()[nutrient]) + amount_num
            month_ref.update({
                    nutrient: amount_num2
            })  
            ##############################

            users_ref.update({
                nutrient: round(amount_num/div,1)
            })


        last_day = calendar.monthrange(today.year, today.month)[1]
        if record_ref.get()['day0'] == 0:
            record_ref.update({
                'month0': today.month,
                'day0': today.day
            })
        
            month_ref.update({
                'days': last_day-record_ref.get()['day0']+1
            })     

        fin.close()

        self.now = 0
        for i in range(self.BuyitemNum+1):
            self.Deleteitem()

        os.remove('./first_process.txt')
        os.remove('./inferText2.txt')
        os.remove('./nutritional_info.txt')
        os.remove('./add_nutritional_info.txt')
        os.remove('./add_nutritional_per.txt')

        self.stackedWidget.setCurrentIndex(0)

    def Recommend(self):
        
        ######################식단 추천 알고리즘 3번째##########################

        path_to_json = './recipes_file' # 후에 json 파일들이 있는 폴더로 위치를 설정해 줄 것
        finding = self.Buyitemingrelist # 나중에 입력을 받아서 그 입력대로 실행할 것
        recommendation = [0] # 여기에 추천되는 식단들 저장
        count = 0

        json_files = [pos_json for pos_json in os.listdir(path_to_json) if pos_json.endswith('.json')] # json 파일을 읽어옴
        for pos_json in json_files:
            with open(path_to_json+'/'+pos_json,'r', encoding = "cp949") as f:
                try:
                    json_data = json.load(f)
                except:
                    continue
                count = 0
                for item in json_data['ingre_list']: # json 파일의 ingre_list -> ingre_name 이 finding의 항목과 일치하면 , 재료를 샀다면 count +1
                    if item['ingre_name'] in finding :
                        count += 1

                # 가장 많은 count를 얻은 식단을 recommendation 에 저장
                if recommendation[0] == count :
                    recommendation.append({json_data['name']:json_data['id']})
                elif recommendation[0] < count :
                    recommendation = []
                    recommendation.append(count)
                    recommendation.append({json_data['name']:json_data['id']})
            f.close()
        length = len(recommendation)
        if length >= 2:
            dictionary = recommendation[random.randrange(1,length)]
        else :
            dictionary = recommendation[1]
        self.recommend = next(iter(dictionary))
        filenumber = dictionary.get(self.recommend)
        self.recommendingredient = ""
        self.recommendurl = ""
        self.recommendstep = ""
        with open(path_to_json+'/'+filenumber+'.json','r', encoding = "cp949") as f2:
            try:
                json_data = json.load(f2)
                for item in json_data['ingre_list']:
                    self.recommendingredient = self.recommendingredient+'\n'+item['ingre_name']
                self.recommendurl =  json_data['url']
                for line in json_data['recipe']:
                    self.recommendstep = self.recommendstep + '\n' +line
                self.recommendpicurl = json_data['thumbnail']
                image = urllib.request.urlopen(self.recommendpicurl).read()
                pixmap = QPixmap()
                pixmap.loadFromData(image)
                p = pixmap.scaled(600,450,Qt.IgnoreAspectRatio)
                self.parent.label_9.setPixmap(p)
                f2.close()
            except:
                f2.close()
                self.recommendingredient = ""
                self.recommendurl = ""
                self.recommendstep = ""
                self.parent.label_9.setText('No Image')
        
        self.stackedWidget.setCurrentIndex(5)
        # print(recommendation[1])
        self.label_10.setText(self.recommend)
        self.label_11.setText(self.recommendingredient)
        self.label_12.setText(self.recommendurl)
        self.label_18.setText(self.recommendstep)


    def Subtract_nutrition(self):
        product_int = self.now + 1
        with open('./nutritional_info.txt','r') as fin:
            data = fin.read().splitlines(True)
        with open('./nutritional_info.txt','w') as fout:
            fout.writelines(data[:product_int-1])
            fout.writelines(data[product_int:])
        fin.close()
        fout.close()
        self.abc.add()
    
    def Total_nutrition(self):
        self.total_nutrition = ""
        fin = open('./add_nutritional_info.txt','r')
        data = fin.readlines()
        for line in data:
            self.total_nutrition = self.total_nutrition + line
            if line[line.find("%")-5:line.find("%")-1].strip().isdigit():
                if int(line[line.find("%")-5:line.find("%")-1].strip()) > 1:
                    self.total_nutrition = self.total_nutrition + " 섭취를 주의하십시오. 100%를 초과하였습니다" + '\n'

        #self.total_nutrition.replace('mg', 'mg\n')
        fin.close()

    def Additem(self):
        if not self.Onemorepicture :
            self.abc.add()
            self.Buyitem.append(self.nutri)
            shutil.copy("./test.png", "./testItemNum"+str(self.BuyitemNum)+".png")
            self.BuyitemNum += 1
            self.Addbuyingrelist()
            buttonReply = QMessageBox.information(None, '추가 사진 등록', "식단 추천을 위해 추가 사진을 등록하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
            if buttonReply == QMessageBox.Yes :
                self.Onemorepicture = True
            else :
                self.Onemorepicture = False
            self.PhotoPage()
        else :
            self.Addbuyingrelist()
            buttonReply = QMessageBox.information(None, '추가 사진 등록', "식단 추천을 위해 추가 사진을 등록하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
            if buttonReply == QMessageBox.Yes :
                self.Onemorepicture = True
            else :
                self.Onemorepicture = False
            self.PhotoPage()
    
    def Addbuyingrelist(self):
        
        self.abc.ingredient()
        if self.abc.ingredientlist == []:
            pass
        else :
            for item in self.abc.ingredientlist:
                if item in self.ingrelist:
                    self.Buyitemingrelist.append(item)

    def Deleteitem(self):
        if self.now == -1 or self.now == self.BuyitemNum:
            self.NoPage()
        elif self.now == self.BuyitemNum-1 :
            self.Buyitem.pop(self.now)
            self.Subtract_nutrition()
            self.now -= 1
            self.BuyitemNum -= 1
            self.StackedPage()
        else :
            self.Buyitem.pop(self.now)
            self.Subtract_nutrition()
            for i in range(1, self.BuyitemNum - self.now):
                shutil.move("./testItemNum"+str(self.now+i)+".png", "./testItemNum"+str(self.now+i-1)+".png")
            self.now -= 1
            self.BuyitemNum -= 1
            self.Next()
        
    def StackedPage(self):
        if not self.BuyitemNum:
            self.NoPage()
            
        elif self.now == -1 :
            self.Total_nutrition()
            self.stackedWidget.setCurrentIndex(3)
            self.label_6.setText("전체 영양성분\n 정보 페이지 입니다")
            self.label_6.setFont(QFont("맑은 고딕", 20))
            self.label_13.setText("전체 영양성분 정보 페이지")
            # image_2 = cv2.imread("./foodimage.png", cv2.IMREAD_COLOR)
            # h,w = image_2.shape[:2]
            # image_2 = cv2.cvtColor(image_2,cv2.COLOR_BGR2RGB)
            # qt_img = QImage(image_2, w, h, QImage.Format_RGB888)
            # pix = QPixmap.fromImage(qt_img) 
            # self.parent.label_14.setPixmap(pix)
            self.label_14.setText(self.total_nutrition)
            self.label_14.setFont(QFont("맑은 고딕", 20))
            # self.parent.label_14.setAlignment(Qt.AlignCenter)
        else:
            self.stackedWidget.setCurrentIndex(3)
            self.label_6.setText(self.Buyitem[self.now])
            self.label_6.setFont(QFont("맑은 고딕", 20))
            self.label_13.setText("현재 페이지 :"+str(self.now+1)+"/ 총 페이지 : "+str(self.BuyitemNum))
            image_2 = cv2.imread("./testItemNum"+str(self.now)+".png", cv2.IMREAD_COLOR)
            h,w = image_2.shape[:2]
            image_2 = cv2.cvtColor(image_2,cv2.COLOR_BGR2RGB)
            qt_img = QImage(image_2, w, h, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qt_img) 
            self.label_14.setPixmap(pix)

    def NoPage(self):
        self.stackedWidget.setCurrentIndex(3)
        self.label_6.setText('NO ITEM')
        self.label_6.setFont(QFont("맑은 고딕", 20))
        # self.parent.label_6.setAlignment(Qt.AlignCenter)
        self.label_13.setText("해당 페이지가 존재하지 않습니다.")
        self.label_14.setText("NO IMAGE")
        self.label_14.setFont(QFont("맑은 고딕", 20))
        # self.parent.label_14.setAlignment(Qt.AlignCenter)

    def Next(self):
        if self.now >= self.BuyitemNum-1 :
            self.NoPage()
            self.now = self.BuyitemNum
        else :
            self.now += 1
            self.StackedPage()

    def Before(self):
        if self.now <= 0 :
            self.now = -1
            self.StackedPage()
        else :
            self.now -= 1
            self.StackedPage()
        
    def PhotoPage(self):
        self.stackedWidget.setCurrentIndex(1)
        self.now = -1

    def ProductPage(self):
        self.stackedWidget.setCurrentIndex(2)
        image_2 = cv2.imread('./test.png', cv2.IMREAD_COLOR)
        h,w = image_2.shape[:2]
        image_2 = cv2.cvtColor(image_2,cv2.COLOR_BGR2RGB)
        qt_img = QImage(image_2, w, h, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qt_img) 
        self.label_4.setPixmap(pix)

        
        #################################
        # this part is for ocr
        #################################
        if not self.Onemorepicture :
            nut_info=open('./nutritional_info.txt','r')
            sys.stdout=open('./abcabc','a')
            print(self.now)
            sys.stdout.close()
            self.nutri = nut_info.readlines()[self.now]
            self.nutri = self.nutri.replace('!','\n')
            self.nutri = self.nutri.replace('칼로리','\n칼로리')
            #self.nutri = self.nutri.replace('끝', '')
            self.label_5.setText(self.nutri)
            self.label_5.setFont(QFont("맑은 고딕", 20))
            nut_info.close()
        else :
            self.label_5.setText("식단 추천을 위한 \n추가 사진촬영 \n페이지 입니다.")
            self.label_5.setFont(QFont("맑은 고딕", 20))


    def AllergyWarning(self):
        # msg = QMessageBox()
        # msg.setIcon(QMessageBox.Critical)
        # msg.setText("알러지 발견")
        # msg.setInformativeText("알러지를 발견했습니다")
        # msg.setWindowTitle("Allergy Detected")
        # msg.exec_()
        AllergyResponse = QMessageBox.information(None, '알러지 발견', "알러지를 발견했습니다, 주의하십시오", QMessageBox.Yes)
            
    def DetectAllergy(self):
        output_file = './output1.json'

        with open(output_file, 'r', encoding='utf-8') as f:
            json_object = json.load(f)


        allergic = ['메밀','대두','호두','땅콩', '잣', '계란','난류',
                    '우유','닭고기','쇠고기','돼지고기','새우','게','고등어',
                    '오징어','복숭아','토마토','아황산','조개류',
                    '굴','전복','홍합']


        detect = []

        for images in json_object['images']:
            for key in images['fields']:

                for i in allergic:
                    if (i in key['inferText']) and (i not in detect):
                        detect.append(i)


        for images in json_object['images']:
            for key in images['fields']:

                if ('밀' in key['inferText']) and ('메밀' not in key['inferText'] ) and ('밀' not in detect ):
                    detect.append('밀')

        f.close()
        return detect



if __name__ == '__main__':
    
    
    app = QApplication(sys.argv)
    currentUi = Ui()
    #currentUi.showMaximized()
    currentUi.show()
    
    
    
    
    sys.exit(app.exec_())