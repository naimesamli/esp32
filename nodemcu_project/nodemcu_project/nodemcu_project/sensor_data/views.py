from django.shortcuts import render, redirect
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
import serial
import threading
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import time
import random
from .models import CapacitorData
from .serializers import CapacitorDataSerializer
serial_connection = None
is_collecting = False
is_random_collecting = False
is_sending = False

class CapacitorDataViewSet(viewsets.ModelViewSet):
    queryset = CapacitorData.objects.all().order_by('-timestamp')
    serializer_class = CapacitorDataSerializer

@api_view(['GET', 'POST'])
def control_data(request):
    global is_sending

    if request.method == 'POST':
        action = request.data.get('action', '')
        if action == 'start':
            is_sending = True
        elif action == 'stop':
            is_sending = False
        return Response({"status": "success", "is_sending": is_sending})

    return HttpResponse("start" if is_sending else "stop")
@csrf_exempt
@api_view(['POST'])
def receive_measurement(request):
    try:
        # JSON verisini almak
        if isinstance(request.data, dict):
            data = request.data
        else:
            import json
            data = json.loads(request.body)

        adc_value = data.get('adc_value')

        # ADC değeri eksikse hata mesajı gönder
        if adc_value is None:
            return Response({"error": "ADC value is None"}, status=status.HTTP_400_BAD_REQUEST)

        # Veri tipini doğrula (integer'a dönüştür)
        try:
            adc_value = int(adc_value)
        except ValueError:
            return Response({"error": "Invalid ADC value, must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        # Kapasitans hesaplama
        estimated_capacity = calculate_capacity(adc_value)

        # Yeni ölçüm kaydını oluştur ve veritabanına kaydet
        measurement = CapacitorData(
            adc_value=adc_value,
            estimated_capacity=estimated_capacity
        )
        measurement.save()

        # Kaydın JSON çıktısını döndür
        return_data = CapacitorDataSerializer(measurement).data
        return Response(return_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        import traceback
        print(f"Hata: {str(e)}")
        print(traceback.format_exc())
        return Response({"error": f"Sunucu hatası: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

# Kapasitans hesaplama fonksiyonu
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

@api_view(['GET'])
def check_status(request):
    global is_collecting, is_random_collecting
    
    status_message = "Bağlantı yok"
    if is_collecting:
        status_message = "Seri port üzerinden veri toplanıyor"
    elif is_random_collecting:
        status_message = "Rastgele veri üretiliyor"
        
    return Response({
        "is_collecting": is_collecting or is_random_collecting,
        "status": status_message
    })

@csrf_exempt
@api_view(['POST'])
def start_serial_collection(request):
    global serial_connection, is_collecting

    try:
        print("Gelen veri:", request.data)
        port = request.data.get('port', 'COM3')
        baud_rate = request.data.get('baud_rate')

        # Baud rate belirtilmemişse varsayılan değeri kullan
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
                print(f"Seri bağlantısı kapatılamadı: {e}")
            serial_connection = None

        try:
            # Sabit 'com3' yerine kullanıcının girdiği port değerini kullan
            serial_connection = serial.Serial(port=port, baudrate=baud_rate, timeout=1)
            is_collecting = True
            threading.Thread(target=collect_serial_data, daemon=True).start()
            return Response({"status": "Veri toplama başlatıldı"})
        except serial.SerialException as e:
            print(f"Seri bağlantı hatası: {e}")
            return Response({"error": f"Seri bağlantı hatası: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        print(f"Beklenmeyen hata: {e}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def collect_serial_data():
    global serial_connection, is_collecting

    while is_collecting and serial_connection:
        try:
            # CPU'yu aşırı yüklememek için küçük bir gecikme ekleyelim
            time.sleep(0.1)

            if serial_connection.in_waiting > 0:
                line = serial_connection.readline().decode('utf-8').strip()
                if line:
                    print(f"Alınan veri: {line}")

                    # Verileri ayrıştırma - ADC değeri olduğunu varsayalım
                    if line.isdigit():
                        adc_value = line  # Burada int yerine string olarak bırakıyoruz
                        if 0 <= int(adc_value) <= 4095:  # ADC aralığını doğrula
                            print(f"ADC Değeri: {adc_value}")
                            estimated_capacity = calculate_capacity(int(adc_value))
                            measurement = CapacitorData(
                                adc_value=adc_value,
                                estimated_capacity=estimated_capacity
                            )
                            measurement.save()
                        else:
                            print(f"Hatalı ADC değeri: {adc_value}")
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

@api_view(['POST'])
def stop_random_collection(request):
    global is_random_collecting
    
    if is_random_collecting:
        is_random_collecting = False
        time.sleep(0.5)
        return Response({"status": "Random data collection stopped"})
    
    return Response({"status": "No random data collection running"})

def collect_random_data():
    global is_random_collecting

    while is_random_collecting:
        try:
            adc_value = random.randint(0, 4095)
            if not (0 <= adc_value <= 4095):
                print(f"Hatalı ADC değeri: {adc_value}")
                continue

            print(f"Üretilen ADC değeri: {adc_value}, Tip: {type(adc_value)}")
            estimated_capacity = calculate_capacity(adc_value)
            measurement = CapacitorData(
                adc_value=adc_value,
                estimated_capacity=estimated_capacity
            )
            measurement.save()
            time.sleep(2)
        except Exception as e:
            print(f"Rastgele veri toplama hatası: {e}")
            time.sleep(1)

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, "Giriş başarılı!")
            return redirect("dashboard")  # Girişten sonra dashboard'a yönlendir
        else:
            messages.error(request, "Geçersiz kullanıcı adı veya şifre!")
    
    return render(request, "login.html")

def user_logout(request):
    logout(request)
    messages.success(request, "Başarıyla çıkış yaptınız.")
    return redirect("login")

def home(request):
    return render(request, "home.html")

@login_required(login_url="login")
def dashboard(request):
    return render(request, "dashboard.html")

def user_register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Yeni kullanıcıyı otomatik olarak giriş yap
            login(request, user)
            return redirect('home')  # Kayıt başarılıysa ana sayfaya yönlendir
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})