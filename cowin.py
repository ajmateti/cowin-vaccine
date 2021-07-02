from datetime import date
import requests
import json
import os
from email_sender import send_email



def get_date():
    from datetime import date
    date = date.today()
    date = date.strftime("%d-%m-%Y")
    return date

def make_request(district='596'):
    date = get_date()
    headers = {
        'authority': 'cdn-api.co-vin.in',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
        'accept': 'application/json, text/plain, */*',
        'sec-ch-ua-mobile': '?0',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
        'origin': 'https://selfregistration.cowin.gov.in',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://selfregistration.cowin.gov.in/',
        'accept-language': 'en-US,en;q=0.9,te;q=0.8',
        'if-none-match': 'W/"6c5f-pzt41cRc9MQtCfQUrk4j2+gBi3g"',
    }

    params = (
        ('district_id', district),
        ('date', date),
    )
    response = requests.get('https://cdn-api.co-vin.in/api/v2/appointment/sessions/calendarByDistrict', headers=headers, params=params)
    return response

def get_response(district):
    for _ in range(10):
        response = make_request(district)
        if response.status_code==200:
            return response.json()

def get_capacity(session):
    available_capacity = session.get('available_capacity')
    available_capacity_dose1 = session.get('available_capacity_dose1')
    available_capacity_dose2 = session.get('available_capacity_dose2')
    capacities = (available_capacity, available_capacity_dose1, available_capacity_dose2)
    if available_capacity>0 or available_capacity_dose1>0 or available_capacity_dose2>0:
        return True, capacities
    return False, capacities

def check(available_slots, district):
    response = get_response(district)
    if response:
        centers = response.get('centers')
        for center in centers:
            for session in center.get('sessions'):
                available, capacity = get_capacity(session)
                if available:
                    obj = {
                        'center': center,
                        'date': session.get('date'),
                        'capacity': capacity,
                        'age': session.get('min_age_limit'),
                        'vaccine': session.get('vaccine'),
                        
                    }
                    available_slots.append(obj)
    if len(available_slots):
        return True

def format_capacity(c):
    return f'Total Doses: {c[0]} Dose 1: {c[1]} Dose 2: {c[2]}'

def get_formatted_message(slots):
    message = ''
    for obj in slots:
        center = obj.get('center')
        name = center.get('name')
        address = center.get('address')
        district = center.get('district_name')
        age = obj.get('age')
        vaccine = obj.get('vaccine')

        capacity = format_capacity(obj.get('capacity'))
        date = obj.get('date')
        message+= f'{name}, {address}, {district}\n {date}\n {capacity}\n Age Limit: {age}\n Vaccine: {vaccine}\n\n'
    return message

def filter_slots(available_slots, vaccine = None, age = None, dose= None):
    ret  = available_slots
    if vaccine:
        ret = filter( lambda x: x['vaccine']==vaccine, ret)
    if age:
        ret = filter( lambda x: x['age']<=age, ret)
    if dose:
        ret = filter( lambda x: x['capacity'][dose]>50, ret)
    return list(ret)


def main():
    available_slots = []
    check(available_slots, district = '581')
    check(available_slots, district = '596')
    print(available_slots)
    lambda_response = []
    for age in [18,45]:
        for vaccine in ['COVISHIELD', 'COVAXIN']:
            for dose in [1,2]:
                x = filter_slots(available_slots, vaccine=vaccine, age=age, dose=dose)
                name = f'{vaccine}_{age}_{dose}'
                if os.getenv(name) is not None and x:
                    lambda_response.append(f'{name} found. Sending Mail.')
                    topic = os.getenv(name)
                    message = get_formatted_message(x) or 'Empty Message'
                    subject = f'{vaccine} available for dose - {dose} for {age}+'
                    response = send_email(topic, message, subject)
                    lambda_response.append(f"Response from mail - {response}")
                elif os.getenv(name):
                    lambda_response.append(f'{name} found. But nothing to update.')
    return lambda_response


def lambda_handler(event, context):
    response = main()
    return {
        'statusCode': 200,
        'body': json.dumps(str(response))
    }
