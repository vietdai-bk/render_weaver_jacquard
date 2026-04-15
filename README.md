# Chieu coi Jacquard 3D

- Chuyển ảnh hoa văn thành ma trận màu (JSON)
- Render lại thành ảnh giả lập dệt Jacquard 3D

## Cấu trúc thư mục

- `convert_json.py`: chuyển ảnh sang JSON
- `weaver_render.py`: render ảnh từ JSON
- `hoa_van/`: chứa ảnh mẫu
- `pattern_library.json`: dữ liệu pattern (tự sinh)

## Cài đặt

1. Clone repository

```
git clone <link-repo>
cd <ten-folder>
```
2. Tạo môi trường ảo

```
python -m venv .env
```
3. Kích hoạt môi trường

Windows:
```
bash
.env\Scripts\activate
```
Hoặc:
```
source .env/bin/activate
```
4. Cài thư viện
```
pip install -r requirements.txt
```
## Cách sử dụng
Tải ảnh cần chuyển thành pattern vào thư mục ```hoa_van/``` rồi thực hiện:  
1. Convert ảnh sang JSON

```bash
python convert_json.py --input hoa_van/ten_anh.jpg --name ten_pattern
```
Kết quả:
- Lưu vào pattern_library.json (với key là ```ten_pattern```)

2. Render ảnh Jacquard

```bash
python weaver_render.py --key ten_pattern
```
Kết quả:
- Ảnh output: realistic_jacquard_ten_pattern.png

3. Ví dụ

Chạy các lệnh sau:
```
python convert_json.py --input hoa_van/ete.jpg --name ete
python weaver_render.py --key ete
```
Xem kết quả là ảnh ```realistic_jacquard_ten_pattern.png```.

4. API

Chạy API Service:
```
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```