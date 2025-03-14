from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import CapacitorData
from .serializers import CapacitorDataSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
import serial
import threading
import time
import random
from django.http import JsonResponse

serial_connection = None
is_collecting = False
is_random_collecting = False

class CapacitorDataViewSet(viewsets.ModelViewSet):
    queryset = CapacitorData.objects.all().order_by('-timestamp')
    serializer_class = CapacitorDataSerializer

@api_view(['POST'])
def receive_measurement(request):
    serializer = CapacitorDataSerializer(data=request.data)
    if serializer.is_valid():
        adc_value = serializer.validated_data.get('adc_value')
        
        if adc_value is None:  
            return Response({"error": "ADC value is None"}, status=status.HTTP_400_BAD_REQUEST)

        adc_value = int(adc_value)  
        estimated_capacity = calculate_capacity(adc_value)

        measurement = CapacitorData(
            adc_value=adc_value,
            estimated_capacity=estimated_capacity
        )
        measurement.save()

        return_data = CapacitorDataSerializer(measurement).data
        return Response(return_data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def calculate_capacity(adc_value):

    return round(adc_value * 0.01, 2)

def dashboard(request):
   
    latest_data = CapacitorData.objects.all().order_by('-timestamp')[:100]
    
    global is_collecting, is_random_collecting
    
    connection_status = "Not connected"
    if is_collecting:
        connection_status = "Connected and collecting from serial"
    elif is_random_collecting:
        connection_status = "Connected and collecting random data"
    
    context = {
        'latest_data': latest_data,
        'connection_status': connection_status
    }
    return render(request, 'dashboard.html', context)

@csrf_exempt
@api_view(['POST'])
def start_serial_collection(request):
    global serial_connection, is_collecting

    try:
        print("Gelen veri:", request.data)
        
        port = request.data.get('port', 'COM3')
        baud_rate = request.data.get('baud_rate')
        
        # Eğer baud_rate None ise varsayılan bir değer ata
        if baud_rate is None:
            baud_rate = 115200
        else:
            baud_rate = int(baud_rate)

        if is_collecting:
            is_collecting = False
            time.sleep(0.5) 

        if serial_connection:
            try:
                serial_connection.close()
            except Exception as e:
                print(f"Serial bağlantısı kapatılamadı: {e}")
            serial_connection = None

        try:
            serial_connection = serial.Serial(port, baud_rate, timeout=1)
            is_collecting = True
            
            threading.Thread(target=collect_serial_data, daemon=True).start()
            return Response({"status": "Data collection started"})
        except serial.SerialException as e:
            print(f"Seri bağlantı hatası: {e}")
            return Response({"error": f"Serial connection error: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        print(f"Beklenmeyen hata: {e}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

def collect_serial_data():

    global serial_connection, is_collecting

    while is_collecting and serial_connection:
        try:
            
            line = serial_connection.readline().decode('utf-8').strip()

            if line: 
                print(f"Alınan veri: {line}")  
                
            else:
                print("Boş veri satırı alındı.")  

        except serial.SerialException as e:
            print(f"Seri port hatası: {e}")
            is_collecting = False
            break

        except Exception as e:
            print(f"Genel hata: {e}")
            time.sleep(1) 

@api_view(['POST'])
def start_random_collection(request):

    global is_collecting, is_random_collecting, serial_connection


    if is_collecting:
        is_collecting = False
        time.sleep(0.5)  
        
        if serial_connection:
            try:
                serial_connection.close()
            except:
                pass
            serial_connection = None
    
    if is_random_collecting:
        is_random_collecting = False
        time.sleep(0.5)  
        return Response({"status": "Random data collection stopped"})
    
    is_random_collecting = True
    threading.Thread(target=collect_random_data, daemon=True).start()
    return Response({"status": "Random data collection started"})

def collect_random_data():
    global is_random_collecting
    
    while is_random_collecting:
        try:
            # ADC değerini üret
            adc_value = random.randint(0, 4095)
            
            # Doğrulama: Aralık dışında mı?
            if not (0 <= adc_value <= 4095):
                print(f"Hatalı ADC değeri: {adc_value}")
                continue
            
            print(f"Üretilen ADC değeri: {adc_value}, Tip: {type(adc_value)}")
            
            # Kapasite hesapla ve kaydet
            estimated_capacity = calculate_capacity(adc_value)
            measurement = CapacitorData(
                adc_value=adc_value,
                estimated_capacity=estimated_capacity(adc_value)
            )
            measurement.save()
            
            time.sleep(2)  
        except Exception as e:
            print(f"Rastgele veri toplama hatası: {e}")
            time.sleep(1)