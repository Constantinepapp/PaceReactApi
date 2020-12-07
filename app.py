from flask import Flask,jsonify,request,json,make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash,check_password_hash
import uuid
import jwt
from functools import wraps
import datetime
from flask_cors import CORS
import pandas as pd 
from datetime import date
import math
from stravalib.client import Client
from httplib2 import Http
import auth
from flask_mail import Mail, Message
import json
import helper_functions


app=Flask(__name__)
CORS(app)

app.config["SECRET_KEY"]="**************"
app.config["SQLALCHEMY_DATABASE_URI"]="**************************" 
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = '******************'
app.config['MAIL_PASSWORD'] = '*****************'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True


mail = Mail(app)
db=SQLAlchemy(app)


class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    public_id=db.Column(db.String(50), unique=True)
    email=db.Column(db.String(50))
    username=db.Column(db.String(50))
    password=db.Column(db.String(300))
    admin=db.Column(db.Boolean)
    rest_hr=db.Column(db.Integer,nullable=False)
    max_hr=db.Column(db.Integer,nullable=False)
    lactate_th=db.Column(db.Integer,nullable=False)
    male = db.Column(db.Boolean,nullable=False)
    age = db.Column(db.Integer,nullable=False)
    measurement_system = db.Column(db.String(50))
    program_start = db.Column(db.DateTime,nullable=True)
    tss_target = db.Column(db.Integer,nullable = True)
    runningProgram = db.Column(db.String,nullable = True)
    planType = db.Column(db.String,nullable = True)
    targetForm = db.Column(db.Integer,nullable = True)
    program_runs_per_week = db.Column(db.Integer,nullable = True)
    strava_connected = db.Column(db.Boolean,nullable=False)
    strava_refresh_token = db.Column(db.String(250),nullable = True)
    last_login=db.Column(db.DateTime,nullable=True)
    number_login = db.Column(db.Integer,nullable = False)
    posts=db.relationship('Activity',backref="athlete",lazy=True)






class Activity(db.Model):
    id= db.Column(db.Integer,primary_key=True)
    strava_id=db.Column(db.Integer,nullable=True)
    date=db.Column(db.DateTime,nullable=False)
    duration=db.Column(db.Float,nullable=False)
    distance=db.Column(db.Float,nullable=False)
    Heart_rate=db.Column(db.Integer,nullable=False)
    up=db.Column(db.Integer,nullable=False)
    down=db.Column(db.Integer,nullable=False)
    running_index=db.Column(db.Float,nullable=False)
    tss=db.Column(db.Float,nullable=False)
    trimp=db.Column(db.Float)
    counts_for_fitness = db.Column(db.Boolean,nullable = False)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)

def token_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message':["danger","token is missing"]})

        try:
            data = jwt.decode(token,app.config['SECRET_KEY'])
            current_user = User.query.filter_by(public_id = data['public_id']).first()
        except:
            return jsonify({'message':["danger","token is invalid"]}),401

        return f(current_user,*args,**kwargs)

    return decorated

@app.route('/register',methods=['POST'])
def new_user():
    data=request.get_json()

    user=User.query.filter_by(email=data["email"]).first()
    user_name = User.query.filter_by(username=data['username']).first()
    if user:
        return jsonify({'message':["warning","email already used on an existing account"]})
    if user_name:
        return jsonify({'message':["warning","username already used"]})
    age = data['age']
    maxhr = 220-int(age)
    if data['male']=="true":
        male = True
    else:
        male = False
    hashed_password = generate_password_hash(data['password'],method='sha256')
    new_user = User(public_id = str(uuid.uuid4()),rest_hr = 60,max_hr = maxhr,lactate_th = round(int(maxhr)*0.9), username = data['username'], password = hashed_password,email = data['email'],admin = False,male=male,age=age,strava_connected= False,measurement_system = "Metric km/hr",number_login = 0)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message':["success","user is created"]})

@app.route('/register_react',methods=['POST'])
def new_user_react():
    data=request.get_json()

    user=User.query.filter_by(email=data["email"]).first()
    user_name = User.query.filter_by(username=data['username']).first()
    if user:
        return jsonify({'message':["warning","email already used on an existing account"]})
    if user_name:
        return jsonify({'message':["warning","username already used"]})
    age = data['age']
    maxhr = 220-int(age)
    if data['male']=="true":
        male = True
    else:
        male = False
    measurement_system = data['measurementSystem']
    hashed_password = generate_password_hash(data['password'],method='sha256')
    new_user = User(public_id = str(uuid.uuid4()),rest_hr = 60,max_hr = maxhr,lactate_th = round(int(maxhr)*0.9), username = data['username'], password = hashed_password,email = data['email'],admin = False,male=male,age=age,strava_connected= False,measurement_system = measurement_system,number_login = 0)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message':["success","user is created"]})


@app.route('/login',methods=['GET'])
def login():
    auth = request.authorization
    print("this is leading pace auth",auth)
    if not auth or not auth.username or not auth.password:
        return jsonify({"message":["danger","something went wrong"]})

    user=User.query.filter_by(username = auth.username).first()
    try:
        user.last_login = date.today()
        user.number_login = user.number_login + 1
        db.session.commit()
    except:
        pass
    if not user:
        return jsonify({"message":["danger","user doen't exist"]})

    if check_password_hash(user.password,auth.password):
        token = jwt.encode({'public_id':user.public_id,'exp':datetime.datetime.utcnow()+datetime.timedelta(minutes=240)},app.config['SECRET_KEY'])
        return jsonify({'token':token.decode('UTF-8'),'email':user.email,'public_id':user.public_id,'max_hr':user.max_hr,'rest_hr':user.rest_hr,'lactate_th':user.lactate_th,"male":user.male,"age":user.age,"strava_connected":user.strava_connected,"strava_refresh_token":user.strava_refresh_token,"measurementSystem":user.measurement_system})
    else:
        return jsonify({"message":["danger","wrong password"]})

@app.route('/login_react',methods=['GET'])
def login_react():
    auth = request.authorization
    print("this is leading pace auth",auth)
    if not auth or not auth.username or not auth.password:
        return jsonify({"message":["danger","something went wrong"]})

    user=User.query.filter_by(email = auth.username).first()
    try:
        user.last_login = date.today()
        user.number_login = user.number_login + 1
        db.session.commit()
    except:
        pass
    if not user:
        return jsonify({"message":["danger","user doen't exist"]})

    if check_password_hash(user.password,auth.password):
        token = jwt.encode({'public_id':user.public_id,'exp':datetime.datetime.utcnow()+datetime.timedelta(minutes=240)},app.config['SECRET_KEY'])
        return jsonify({'token':token.decode('UTF-8'),'email':user.email,'public_id':user.public_id,'max_hr':user.max_hr,'rest_hr':user.rest_hr,'lactate_th':user.lactate_th,"male":user.male,"age":user.age,"strava_connected":user.strava_connected,"strava_refresh_token":user.strava_refresh_token,"measurementSystem":user.measurement_system})
    else:
        return jsonify({"message":["danger","wrong password"]})

@app.route('/dashboard')
@token_required
def show_entries(current_user):
    date_list=Activity.query.with_entities(Activity.date).filter_by(user_id=current_user.id).order_by(Activity.date.asc()).filter_by(counts_for_fitness = True)
    Rundex_list=Activity.query.with_entities(Activity.running_index).filter_by(user_id=current_user.id).order_by(Activity.date.asc()).filter_by(counts_for_fitness = True)
    
    #this lines make a list out of list of turples
    date_list=[value for (value,) in date_list]
    Rundex_list=[value for (value,) in Rundex_list]

    #check if user has entered at least 3 activities to avoid out of index error
    if len(Rundex_list)<3:
        return jsonify({'message':["warning","add at least 3 activities. Before adding activities add your Maximum and Rest heart rate first from the user tab.Ignore this message if you have already done that."]})


    try:
        Rundex_median = [Rundex_list[0],Rundex_list[1]]
        for i in range(2,10):
            Rundex_median.append((Rundex_median[i-1]+Rundex_median[i-2]+Rundex_list[i])/3)
        for i in  range(10,len(Rundex_list)):
            median=(Rundex_list[i-10]+Rundex_list[i-9]+Rundex_list[i-8]+Rundex_list[i-7]+Rundex_list[i-6]+Rundex_list[i-5]+Rundex_list[i-4]+Rundex_list[i-3]+Rundex_list[i-2]+Rundex_list[i-1]+Rundex_list[i])/11
            median=round(median,1)
            Rundex_median.append(median)
    except:    
        try:
            
            Rundex_median=[Rundex_list[0]]
            for i in range(1,10):
                Rundex_median.append((Rundex_median[i-1]+Rundex_list[i])/2)
            for i in  range(5,len(Rundex_list)):
                median=(Rundex_list[i-5]+Rundex_list[i-4]+Rundex_list[i-3]+Rundex_list[i-2]+Rundex_list[i-1]+Rundex_list[i])/6
                median=round(median,1)
                Rundex_median.append(median)
        except:
            #give Rundex_median 2 starting values so i dont get an error
            Rundex_median=[Rundex_list[0],Rundex_list[1]]
            for i in  range(2,len(Rundex_list)):
                median=(Rundex_list[i-2]+Rundex_list[i-1]+Rundex_list[i])/3
                median=round(median,1)
                Rundex_median.append(median)

    VO2max=(Rundex_median[-1]*1.1175)-11.2879
    VO2max=round(VO2max,1)




    return jsonify({'running_index':Rundex_list,'median':Rundex_median,"date":date_list,"VO2max":VO2max})


@app.route('/traininghistory')
@token_required
def training_history(current_user):
    entries=Activity.query.filter_by(user_id = current_user.id).order_by(Activity.date.desc())

    output=[]

    for entry in entries:
        entries_dic = {}
        entries_dic['id'] = entry.id
        entries_dic['date'] = entry.date
        entries_dic['distance'] = entry.distance
        entries_dic['duration'] = entry.duration
        entries_dic['avgHr'] = entry.Heart_rate
        entries_dic['runningIndex']=entry.running_index
        entries_dic['stressScore']=entry.tss
        entries_dic['ascent']=entry.up
        entries_dic['descent']=entry.down
        entries_dic['counts']=entry.counts_for_fitness
        output.append(entries_dic)


    return jsonify({'entries':output})

@app.route('/trainingzones')
@token_required
def trainingzones(current_user):

    Rundex_list=Activity.query.with_entities(Activity.running_index).filter_by(user_id=current_user.id).order_by(Activity.date.asc())



    Running_fitness_list=[value for (value,) in Rundex_list]

    #check if user has entered at least 3 activities to avoid out of index error
    if len(Running_fitness_list)<3:
        return jsonify({'message':["warning","add at least 3 activities"]})

    Running_fitness=(Running_fitness_list[-1]+Running_fitness_list[-2]+Running_fitness_list[-3])/3
    Running_fitness=round(Running_fitness,1)

    Running_fitness_int=int(Running_fitness)

    aerobic_one_speed = 0.21*Running_fitness - 0.68
    Aerobic_speed_theory=(Running_fitness-5.668)/3.82
    Tempo_speed_theory=(Running_fitness-2.84)/3.75
    interval_95_percent_vo2max = Running_fitness * 0.2979 - 0.8774



    Tempo_speed_theory=round(Tempo_speed_theory,2)
    #Aerobic_speed=round(Aerobic_speed,2)
    Aerobic_speed_theory=round(Aerobic_speed_theory,2)

    #Tempo_speed=(Running_fitness-11.84)/3.13
    #Tempo_speed=round(Tempo_speed,2)


    rest=int(current_user.rest_hr)
    maxh=int(current_user.max_hr)
    reserve=maxh-rest
    print(maxh,rest)

    aer1=int(rest+reserve*0.6)
    aer2=int(rest+reserve*0.7)
    aer3=int(rest+(reserve*0.7)+1)
    aer4=int(rest+reserve*0.8)
    thre1=int(rest+(reserve*0.8)+1)
    thre2=int(rest+reserve*0.9)
    max1=int(rest+(reserve*0.9)+1)


    return jsonify({'running_index':Running_fitness_int,'aer1':aer1,"aer2":aer2,"aer3":aer3,"aer4":aer4,"thre1":thre1,"thre2":thre2,"max1":max1,"max2":maxh,"aerobicSpeed":Aerobic_speed_theory,"threSpeed":Tempo_speed_theory,"intervalSpeed":interval_95_percent_vo2max,"aerobicOneSpeed":aerobic_one_speed})

@app.route('/trainingload')
@token_required
def show_archived(current_user):

    timeFrame = request.headers['timeFrame']
    today = date.today()
    if timeFrame == "two":
        data_raw=Activity.query.filter_by(user_id = current_user.id).filter(Activity.date.between(today-datetime.timedelta(days=730),today))
    elif timeFrame == "all":
        data_raw=Activity.query.filter_by(user_id = current_user.id).all()
    else:
        data_raw=Activity.query.filter_by(user_id = current_user.id).filter(Activity.date.between(today-datetime.timedelta(days=365),today))



    date_list=[]
    tss_list=[]

    for item in data_raw:
        #dat=datetime.datetime.strptime(item.date,'%m/%d/%Y')
        date_list.append(item.date)
        tss_list.append(item.tss)

    #check if user has entered at least 3 activities to avoid out of index error
    if len(date_list)<3:
        return jsonify({'message':["warning","add at least 3 activities"]})

    today_last=date.today()+datetime.timedelta(days=30)
    date_list.append(today_last)
    tss_list.append(0.00)


    df = pd.DataFrame(
        {'Date': date_list,
        'tss': tss_list,
        })


    df = df.set_index('Date')
    series=df.resample('d').tss.sum()


    frame=pd.DataFrame({'Date':series.index, 'tss':series.values})

    frame['fitness']=0.00
    frame['fatigue']=0.00
    frame['form']=0.00
    for i in range(1,len(frame)):
        frame['fitness'][i]=frame['fitness'][i-1]+(frame['tss'][i]-frame['fitness'][i-1])*(1-math.exp(-1/42))
        frame['fatigue'][i]=frame['fatigue'][i-1]+(frame['tss'][i]-frame['fatigue'][i-1])*(1-math.exp(-1/7))
        frame['form'][i]=frame['fitness'][i-1]-frame['fatigue'][i-1]


    fatigue_current=round(frame['fatigue'].iloc[-1],2)
    fitness_current=round(frame['fitness'].iloc[-1],2)
    form_current=round(frame['form'].iloc[-1],2)

    fatigue=frame['fatigue'].tolist()
    fitness = frame['fitness'].tolist()
    form = frame['form'].tolist()
    dateList = frame['Date'].tolist()

    return jsonify({'fitness':fitness,'fatigue':fatigue,'form':form,'date':dateList})


@app.route("/weeklymileage",methods=["GET"])
@token_required
def weeklymileage(current_user):
    
    timeFrame = request.headers['timeFrame']
    timeScale = request.headers['timeScale']
    today = date.today()
    
    if timeFrame == "two":
        data_raw=Activity.query.filter_by(athlete=current_user).filter(Activity.date.between(today-datetime.timedelta(days=730),today))
    elif timeFrame == "all":
        data_raw=Activity.query.filter_by(athlete=current_user)    
    else:
        data_raw=Activity.query.filter_by(athlete=current_user).filter(Activity.date.between(today-datetime.timedelta(days=365),today))
    #check if user has entered at least 3 activities to avoid out of index error

    if not timeScale:
        timeScale = "m"
        
    date_list=[]
    distance_list=[]

    

    for item in data_raw:
        date_list.append(item.date)
        distance_list.append(item.distance)



    if len(date_list)<3:
        return jsonify({'message':["warning","add at least 3 activities"]})


    #created pandas dataframe from the two lists
    date_list.append(date.today())
    distance_list.append(0.00)
    

    df = pd.DataFrame(
        {'Date': date_list,
        'Distance': distance_list,
        'week':''
        })

    #created a series of first day of the week so one entry for each week and the sum of distance for each week
    df = df.set_index('Date')
    series=df.resample(timeScale).Distance.sum()

    # tranformed the series to a dataframe again and named the two columns as "Date" and "Sum"

    week_sum=pd.DataFrame({'Date':series.index, 'Sum':series.values})

    weeklymeters = week_sum['Sum'].tolist()

    dateList = week_sum['Date'].tolist()
    if timeScale == "y":
        dateList = [date.year for date in dateList]
    if timeScale == "m":
        dateList = [str(date.month)+"/"+str(date.year) for date in dateList]
    if timeScale == "w":
        dateList = [str(date.day)+"/"+str(date.month)+"/"+str(date.year) for date in dateList]
    
    weeklymileage = [x/1000 for x in weeklymeters]
    weeklymileage = [round(x,2) for x in weeklymileage]

    return jsonify({'date':dateList,'weeklymilage':weeklymileage})


@app.route("/weeklyStressScore",methods=["GET"])
@token_required
def weeklyStressScore(current_user):

    data_raw=Activity.query.filter_by(athlete=current_user)
    #check if user has entered at least 3 activities to avoid out of index error

    date_list=[]
    tss_list=[]


    for item in data_raw:
        date_list.append(item.date)
        tss_list.append(item.tss)



    if len(date_list)<3:
        return jsonify({'message':["warning","add at least 3 activities"]})


    #created pandas dataframe from the two lists

    date_list.append(date.today())
    tss_list.append(0.00)

    df = pd.DataFrame(
        {'Date': date_list,
        'Tss': tss_list,
        'week':''
        })

    #created a series of first day of the week so one entry for each week and the sum of distance for each week

    df = df.set_index('Date')
    series=df.resample('w').Tss.sum()

    # tranformed the series to a dataframe again and named the two columns as "Date" and "Sum"

    week_sum=pd.DataFrame({'Date':series.index, 'Sum':series.values})

    weeklystress = week_sum['Sum'].tolist()

    dateList = week_sum['Date'].tolist()

    return jsonify({'date':dateList,'tss':weeklystress})



@app.route('/createentry',methods=['POST'])
@token_required
def create_entry(current_user):
    data=request.get_json()
    date = datetime.datetime.strptime(data['date'],'%m/%d/%Y')
    new_entry=Activity(date=date,duration=data['time'],distance=data['distance'],Heart_rate=data["hr"],up=data['up'],down=data['down'],running_index=data['runningIndex'],tss=data['tss'],trimp=data['trimp'],counts_for_fitness = True,athlete=current_user)
    db.session.add(new_entry)
    db.session.commit()

    return jsonify({"message":["success","success"]})

@app.route('/bulk_import',methods=['POST'])
@token_required
def bulk_import(current_user):
    csv=request.get_json()
    for data in csv:
        
        try:
            date = datetime.datetime.strptime(data['date'],'%m/%d/%Y')
            new_entry=Activity(date=date,duration=data['duration'],distance=data['distance'],Heart_rate=data["hr"],up=data['up'],down=data['down'],running_index=data['runningIndex'],tss=data['tss'],trimp=data['trimp'],counts_for_fitness = True,athlete=current_user)
            db.session.add(new_entry)
        except KeyError:
            pass
        except ValueError:
            pass

    db.session.commit()
    return jsonify({"message":["success","success"]})

@app.route('/strava_auth',methods=['POST'])
@token_required
def strava_authenticate(current_user):
    data=request.get_json()
    if current_user.strava_connected:
        return jsonify({"message":["warning","user is already authenticated, if there is a problem with sync deauthorize and authorize again"]})
    strava_auth_token = auth.strava_auth(data['authCode'])
    print(strava_auth_token)
    user=current_user
    
    print(strava_auth_token)

    if strava_auth_token:
        user.strava_connected = True
        user.strava_refresh_token = strava_auth_token['refresh_token']
        db.session.commit()
        return jsonify({'data':strava_auth_token['refresh_token'],"strava_connected":True,"message":["success","strava auth success"]})
    else:
        return jsonify({"message":["danger","strava auth token not exists"]})

@app.route('/strava_refresh_token',methods=['POST'])
@token_required
def strava_refresh_token(current_user):
    data=request.get_json()
    access_token = auth.strava_refresh_token(data['refreshToken'])
    user=current_user

    print(access_token)

    if access_token:
        return jsonify({'access_token':access_token})
    else:
        return jsonify({"message":"something went wrong with the strava refresh token"})

@app.route('/strava_import',methods=['POST'])
@token_required
def strava_import(current_user):
    data=request.get_json()
    
    for activity in data:
        entry=Activity.query.filter_by(strava_id=activity["id"]).first()
        if entry:
            pass
        else:
            try:
                date = datetime.datetime.strptime(activity['date'],'%Y-%m-%dT%H:%M:%SZ')
                new_entry=Activity(strava_id=activity['id'],date=date,duration=activity['duration'],distance=activity['distance'],Heart_rate=activity["hr"],up=activity['up'],down=activity['down'],running_index=activity['runningIndex'],tss=activity['tss'],trimp=activity['trimp'],counts_for_fitness = True,athlete=current_user)
                db.session.add(new_entry)
            except KeyError:
                pass
            except ValueError:
                pass

    db.session.commit()
    return jsonify({"message":["success","activities were saved"],"data":data})

@app.route('/deleteentry',methods=['DELETE'])
@token_required
def delete_entry(current_user):
    data=request.get_json()
    print(data)
    entry=Activity.query.filter_by(id=data["id"]).first()

    if entry.user_id != current_user.id:
        return jsonify({"message":"not authorized"})

    if entry:
        db.session.delete(entry)
        db.session.commit()
        return jsonify({"message":["success","entry deleted"]})

    return jsonify({"message":["danger","something went wrong"]})

@app.route('/countsforfitness',methods=['PUT'])
@token_required
def counts_for_fitness(current_user):

    data=request.get_json()
    entry=Activity.query.filter_by(id=data["id"]).first()

    if entry.user_id != current_user.id:
        return jsonify({"message":"not authorized"})
    print( data['counts'])
    if entry:
        if data['counts'] == False:
            entry.counts_for_fitness = False
            db.session.commit()
            return jsonify({"message":["warning","activity is excluded from fitness estimation"]})
        else:
            entry.counts_for_fitness = True
            db.session.commit()
            return jsonify({"message":["success","activity is included in fitness estimation"]})

    return jsonify({"message":["danger","something went wrong"]})

@app.route('/countsforfitnessreact',methods=['PUT'])
@token_required
def counts_for_fitness_react(current_user):

    data=request.get_json()
    entry=Activity.query.filter_by(id=data["id"]).first()

    if entry.user_id != current_user.id:
        return jsonify({"message":"not authorized"})
    
    if entry:
        entry.counts_for_fitness = not entry.counts_for_fitness
        db.session.commit()
        return jsonify({"message":["warning","success"]})
        

    return jsonify({"message":["danger","something went wrong"]})

@app.route('/generateprogram',methods=['PUT'])
@token_required
def generateprogram(current_user):
    data=request.get_json()
    user=User.query.filter_by(id=current_user.id).first()
    user.program_start = date.today()
    user.tss_target = data["tss_target"]
    user.targetForm = data["targetForm"]
    runningProgram = data['runningProgram']
    user.planType = data['planType']
    user.runningProgram = json.dumps(runningProgram)
    user.program_runs_per_week = data['program_runs_per_week']
    

    db.session.commit()

    return jsonify({'message':["success","program has started"]})


@app.route("/showprogram",methods=["GET"])
@token_required
def showprogram(current_user):

    user=User.query.filter_by(id=current_user.id).first()
    planType = "--"
    try:
        planType = user.planType
    except:
        pass
    try:
        program_start=user.program_start
        end_date=program_start + datetime.timedelta(days=28)
        runningProgram = user.runningProgram
        runningProgram = json.loads(runningProgram)
        targetForm = user.targetForm
        program_runs_per_week = user.program_runs_per_week
        
    except:
        return jsonify({'message':["danger","no training program exists"]})

    week_one = program_start + datetime.timedelta(days=7)
    week_two = week_one + datetime.timedelta(days=7)
    week_three = week_two + datetime.timedelta(days=7)
    week_four = week_three + datetime.timedelta(days=7)

    data_raw=Activity.query.filter_by(athlete=current_user).filter(Activity.date >= program_start,Activity.date <= end_date).all()
    #check if user has entered at least 3 activities to avoid out of index error

    

    tss_until_now=0
    tss_target = user.tss_target
    for item in data_raw:
        tss_until_now = tss_until_now + item.tss



    return jsonify({'tss_until_now':tss_until_now,'targetForm':targetForm,'tss_target':tss_target,"program_runs_per_week":program_runs_per_week,"program_start":program_start.strftime("%m/%d/%Y") ,"program_ends":end_date.strftime("%m/%d/%Y"),"weekDates":[program_start.strftime("%m/%d/%Y"),week_one.strftime("%m/%d/%Y"),week_two.strftime("%m/%d/%Y"),week_three.strftime("%m/%d/%Y"),week_four.strftime("%m/%d/%Y")],"runningProgram":runningProgram,"planType":planType})



@app.route("/account",methods=['PUT'])
@token_required
def account(current_user):
    data = request.get_json()
    user=User.query.filter_by(id=current_user.id).first()

    if not user:
        return jsonify({"message":["danger","not authorized"]})

    user.rest_hr = data["rest_hr"]
    user.max_hr = data['max_hr']
    user.lactate_th =data['lactate']
    user.username = data['username']
    user.measurement_system = data['measurementSystem']
    if data['sex']=='Female':
        user.male = False
    else:
        user.male = True
    if data['password']!="":
        hashed_password = generate_password_hash(data['password'],method='sha256')
        user.password = hashed_password
    user.age = data['age']
    db.session.commit()


    return jsonify({"message":"account updated"})


@app.route("/user",methods=['GET'])
@token_required
def user(current_user):
    
    user=User.query.filter_by(id = current_user.id).first()
    if not user:
        return jsonify({"message":["danger","something went wrong"]})

    return jsonify({'username':user.username,'email':user.email,'public_id':user.public_id,'max_hr':user.max_hr,'rest_hr':user.rest_hr,'lactate_th':user.lactate_th,"male":user.male,"age":user.age,"strava_connected":user.strava_connected,"strava_refresh_token":user.strava_refresh_token,"measurementSystem":user.measurement_system})
    
@app.route('/strava_import_react',methods=['POST'])
@token_required
def strava_import_react(current_user):
    data=request.get_json()
    
    
    for activity in data['activities']:
        entry=Activity.query.filter_by(strava_id=activity["id"]).first()
        if entry:
            pass
        else:
            try:
                date = datetime.datetime.strptime(activity['date'],'%Y-%m-%dT%H:%M:%SZ')
                if activity['hr'] == 0:
                    hr = 0
                    runningIndex = 0
                    tss = 0
                    trimp = 0
                    counts= False
                else:
                    hr = activity['hr']
                    runningIndex = helper_functions.calc_running_index(activity,current_user)
                    tss,trimp = helper_functions.calc_trimp_tss(activity,current_user)
                    counts = True
                new_entry=Activity(strava_id=activity['id'],date=date,duration=activity['duration'],distance=activity['distance'],Heart_rate=int(hr),up=activity['up'],down=activity['down'],running_index=runningIndex,tss=tss,trimp=trimp,counts_for_fitness = counts,athlete=current_user)
                db.session.add(new_entry)
            except KeyError as e: print(e)
                
            except ValueError as e: print(e)
                

    db.session.commit()
    return jsonify({"message":["success","activities were saved"],"data":data})


@app.route('/create_single_entry',methods=['POST'])
@token_required
def create_single_entry(current_user):
    data=request.get_json()
    print(data)
    date = datetime.datetime.strptime(data['date'],'%Y-%m-%d')
    new_entry=Activity(date=date,duration=data['time'],distance=data['distance'],Heart_rate=data["hr"],up=data['up'],down=data['down'],running_index=data['runningIndex'],tss=data['tss'],trimp=data['trimp'],counts_for_fitness = True,athlete=current_user)
    db.session.add(new_entry)
    db.session.commit()

    return jsonify({"message":["success","activity saved"]})

@app.route('/strava_unpair',methods=['DELETE'])
@token_required
def strava_unpair(current_user):

    current_user.strava_connected = False
    current_user.strava_refresh_token = ''

    db.session.commit()
    return jsonify({"message":["success","your strava auth code is deleted, go to strava.com and de authorize leading pace app from the settings"]})

@app.route("/password_reset",methods=['POST'])
def password_reset():
    data = request.get_json()

    user=User.query.filter_by(email = data["email"]).first()

    if not user:
        return jsonify({"message":["danger","there is not a user with this mail"]})

    token = jwt.encode({'public_id':user.public_id,'exp':datetime.datetime.utcnow()+datetime.timedelta(minutes=120)},app.config['SECRET_KEY'])
    token = token.decode('UTF-8')
    msg = Message("Password Reset",sender ='leadingpacerunningapp@gmail.com',recipients = ['constantinepapp@outlook.com'])
    msg.body = "copy this token without the braces        [{}]        and paste it on the field on the page".format(token)
    mail.send(msg)
    return jsonify({'public_id':user.public_id,'message':["success","Check your mail"]})

@app.route("/new_password",methods=['PUT'])
@token_required
def new_password(current_user):
    data=request.get_json()
    print(data['password'])
    user=User.query.filter_by(id=current_user.id).first()
    if not user:
        return jsonify({'message':["danger","token is expired or wrong, please make sure to not copy blank spaces with the token"]})
    hashed_password = generate_password_hash(data['password'],method='sha256')
    user.password = hashed_password
    db.session.commit()
    return jsonify({'message':["success","passwork was updated"]})

@app.route("/admin_all",methods=['GET'])
@token_required
def admin_all(current_user):
    data=request.get_json()
    user=User.query.filter_by(id = current_user.id).first()

    if user.admin:
        users = User.query.all()
        data_raw=Activity.query.all()
        users_list = []
        
        for user in users:
            activities = 0
            users_dic = {}
            users_dic['id'] = user.id
            users_dic['email'] = user.email
            users_dic['username'] = user.username
            users_dic['rest_hr'] = user.rest_hr
            users_dic['admin'] = user.admin
            users_dic['max_hr'] = user.max_hr
            users_dic['male'] = user.male
            users_dic['age'] = user.age
            users_dic['last_login'] = user.last_login
            users_dic['number_login'] = user.number_login
            for activity in data_raw:
                if activity.user_id == user.id :
                    activities = activities + 1
            users_dic['activities'] = activities
                
            users_list.append(users_dic)

        return jsonify({"users":users_list})
    else:
        return jsonify({'message':["danger","user is not admin"]})
    

@app.route("/make_admin",methods=['PUT'])
@token_required
def make_admin(current_user):
    data=request.get_json()
    user=User.query.filter_by(id = current_user.id).first()
    
    user.admin = True
    db.session.commit()    
    
    return jsonify({'message':["success","user is admin"]})

@app.route("/contact",methods=['POST'])
@token_required
def contact(current_user):
    data = request.get_json()

    emailSender = current_user.email
   
    msg = Message(data['subject'],sender = emailSender,recipients = ['leadingpacerunningapp@gmail.com'])
    msg.body = data['body']
    mail.send(msg)
    return jsonify({'message':["success","Thank you for your feedback"]})


@app.route('/get_user_posts',methods=['GET'])
@token_required
def get_user_posts(current_user):
    data = request.get_json()
    print(data)
    entries=Activity.query.filter_by(user_id = current_user.id).order_by(Activity.date)

    output=[]

    for entry in entries:
        entries_dic = {}
        entries_dic['id'] = entry.id
        entries_dic['date'] = entry.date
        entries_dic['distance'] = entry.distance
        entries_dic['duration'] = entry.duration
        entries_dic['avgHr'] = entry.Heart_rate
        entries_dic['runningIndex']=entry.running_index
        entries_dic['stressScore']=entry.tss
        entries_dic['ascent']=entry.up
        entries_dic['descent']=entry.down
        entries_dic['counts'] = entry.counts_for_fitness
        output.append(entries_dic)


    return jsonify({'entries':output})

@app.route("/edit_account",methods=['PUT'])
@token_required
def edit_account(current_user):
    data = request.get_json()
    user=User.query.filter_by(id=current_user.id).first()

    if not user:
        return jsonify({'message':["danger","token is expired or wrong, please make sure to not copy blank spaces with the token"]})
    try:
        if data['password']:
            hashed_password = generate_password_hash(data['password'],method='sha256')
            user.password = hashed_password
            db.session.commit()
            return jsonify({'message':["success","passwork was updated"]})
    except:
        pass
        

    user.rest_hr = data["rest_hr"]
    user.max_hr = data['max_hr']
    user.lactate_th =data['lactate_th']
    user.username = data['username']
    user.measurement_system = data['measurementSystem']
    
    if data['male'] == 'true':
        user.male = True
    else:
        user.male = False
    
    
    ##if data['password']!="":
    ##    hashed_password = generate_password_hash(data['password'],method='sha256')
    ##    user.password = hashed_password
    user.age = data['age']
    db.session.commit()

    return jsonify({"message":"account updated"})


    
if __name__=="__main__":
    app.run(debug=True)