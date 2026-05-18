# TODO - Sửa lỗi quét nhầm đối tượng

- [ ] B1: Dọn `call_gemini_for_change()` bỏ phần code thừa (đoạn prompt/return thứ 2 không chạy nhưng đang gây nhiễu/khó bảo trì) chỉ giữ 1 luồng.
- [ ] B2: Siết prompt Gemini để trả thêm `Matched_Target` và nếu `Matched_Target=false` thì ép `Is_Activity=false`.
- [ ] B3: Đổi cơ chế chống trùng history từ `set(url)` sang `set((target.name, url))`.
- [ ] B4: Chạy `python monitor.py` (hoặc endpoint `/monitor/run`) để kiểm tra logs và xem nhãn target trên dashboard còn bị nhầm hay không.

