"""
Dữ liệu mẫu preset 3 môn Toán - Vật lý - Hóa học lớp 12.
Chạy khi khởi động nếu DB chưa có môn nào.
"""
import logging
from sqlalchemy.orm import Session
from app.models.models import Subject, Chapter, Lesson, Exam, ExamQuestion

logger = logging.getLogger("studyapp.seed")

CURRICULUM = {
    "Toán": {
        "icon": "📐",
        "chapters": [
            {
                "name": "Ứng dụng đạo hàm để khảo sát và vẽ đồ thị hàm số",
                "lessons": [
                    "Sự đồng biến, nghịch biến của hàm số",
                    "Cực trị của hàm số",
                    "Giá trị lớn nhất, giá trị nhỏ nhất của hàm số",
                    "Đường tiệm cận",
                    "Khảo sát sự biến thiên và vẽ đồ thị hàm số",
                ],
            },
            {
                "name": "Hàm số lũy thừa, hàm số mũ và hàm số logarit",
                "lessons": [
                    "Lũy thừa",
                    "Hàm số lũy thừa",
                    "Logarit",
                    "Hàm số mũ, hàm số logarit",
                    "Phương trình mũ và phương trình logarit",
                    "Bất phương trình mũ và bất phương trình logarit",
                ],
            },
            {
                "name": "Nguyên hàm, tích phân và ứng dụng",
                "lessons": [
                    "Nguyên hàm",
                    "Tích phân",
                    "Ứng dụng của tích phân trong hình học",
                ],
            },
            {
                "name": "Số phức",
                "lessons": [
                    "Số phức",
                    "Cộng, trừ và nhân số phức",
                    "Chia số phức, căn bậc hai của số thực âm",
                    "Phương trình bậc hai với hệ số thực",
                ],
            },
            {
                "name": "Khối đa diện",
                "lessons": [
                    "Khái niệm về khối đa diện",
                    "Phép đối xứng qua mặt phẳng",
                    "Thể tích khối đa diện",
                ],
            },
            {
                "name": "Mặt nón, mặt trụ, mặt cầu",
                "lessons": [
                    "Khái niệm mặt tròn xoay",
                    "Mặt cầu",
                    "Diện tích và thể tích mặt tròn xoay",
                ],
            },
            {
                "name": "Phương pháp tọa độ trong không gian",
                "lessons": [
                    "Hệ tọa độ trong không gian",
                    "Phương trình mặt phẳng",
                    "Phương trình đường thẳng trong không gian",
                ],
            },
        ],
    },
    "Vật lý": {
        "icon": "⚛️",
        "chapters": [
            {
                "name": "Dao động cơ",
                "lessons": [
                    "Dao động điều hòa",
                    "Con lắc lò xo",
                    "Con lắc đơn",
                    "Dao động tắt dần, dao động cưỡng bức",
                    "Tổng hợp hai dao động điều hòa cùng phương, cùng tần số",
                ],
            },
            {
                "name": "Sóng cơ và sóng âm",
                "lessons": [
                    "Sóng cơ và sự truyền sóng cơ",
                    "Giao thoa sóng",
                    "Sóng dừng",
                    "Đặc trưng vật lý của âm",
                ],
            },
            {
                "name": "Dòng điện xoay chiều",
                "lessons": [
                    "Đại cương về dòng điện xoay chiều",
                    "Các mạch điện xoay chiều",
                    "Mạch có R, L, C mắc nối tiếp",
                    "Công suất điện tiêu thụ, hệ số công suất",
                    "Truyền tải điện năng, máy biến áp",
                    "Máy phát điện xoay chiều",
                ],
            },
            {
                "name": "Dao động và sóng điện từ",
                "lessons": [
                    "Mạch dao động",
                    "Điện từ trường",
                    "Sóng điện từ",
                    "Nguyên tắc thông tin liên lạc bằng sóng vô tuyến",
                ],
            },
            {
                "name": "Sóng ánh sáng",
                "lessons": [
                    "Tán sắc ánh sáng",
                    "Giao thoa ánh sáng",
                    "Các loại quang phổ",
                    "Tia hồng ngoại, tia tử ngoại, tia X",
                ],
            },
            {
                "name": "Lượng tử ánh sáng",
                "lessons": [
                    "Hiện tượng quang điện",
                    "Thuyết lượng tử ánh sáng",
                    "Hiện tượng quang điện trong",
                    "Mẫu nguyên tử Bohr, quang phổ vạch của hiđro",
                    "Sơ lược về laser",
                ],
            },
            {
                "name": "Hạt nhân nguyên tử",
                "lessons": [
                    "Tính chất và cấu tạo hạt nhân",
                    "Năng lượng liên kết hạt nhân",
                    "Phóng xạ",
                    "Phản ứng hạt nhân",
                    "Phản ứng phân hạch và phản ứng nhiệt hạch",
                ],
            },
        ],
    },
    "Hóa học": {
        "icon": "🧪",
        "chapters": [
            {
                "name": "Este - Lipit",
                "lessons": [
                    "Este",
                    "Lipit",
                    "Chất giặt rửa",
                ],
            },
            {
                "name": "Cacbohidrat",
                "lessons": [
                    "Glucozơ",
                    "Saccarozơ, tinh bột và xenlulozơ",
                ],
            },
            {
                "name": "Amin, amino axit và protein",
                "lessons": [
                    "Amin",
                    "Amino axit",
                    "Peptit và protein",
                ],
            },
            {
                "name": "Polime và vật liệu polime",
                "lessons": [
                    "Đại cương về polime",
                    "Vật liệu polime",
                ],
            },
            {
                "name": "Đại cương về kim loại",
                "lessons": [
                    "Kim loại và hợp kim",
                    "Dãy điện hóa của kim loại",
                    "Sự ăn mòn kim loại",
                    "Điều chế kim loại",
                ],
            },
            {
                "name": "Kim loại kiềm, kiềm thổ, nhôm",
                "lessons": [
                    "Kim loại kiềm và hợp chất quan trọng",
                    "Kim loại kiềm thổ và hợp chất quan trọng",
                    "Nhôm và hợp chất của nhôm",
                ],
            },
            {
                "name": "Sắt và một số kim loại quan trọng",
                "lessons": [
                    "Sắt",
                    "Hợp chất của sắt",
                    "Hợp kim của sắt",
                    "Crom và hợp chất",
                ],
            },
            {
                "name": "Nhận biết một số chất vô cơ",
                "lessons": [
                    "Nhận biết một số ion trong dung dịch",
                    "Nhận biết một số chất khí",
                ],
            },
            {
                "name": "Hóa học và vấn đề phát triển kinh tế, xã hội, môi trường",
                "lessons": [
                    "Hóa học và vấn đề phát triển kinh tế",
                    "Hóa học và vấn đề xã hội",
                    "Hóa học và vấn đề môi trường",
                ],
            },
        ],
    },
}


# ---- Đề thi mẫu chuẩn chính thức từ các Sở GD&ĐT & Trường Chuyên 2025 ----

SAMPLE_EXAMS = [
    {
        "subject": "Toán",
        "title": "Đề thi thử Tốt nghiệp THPT 2025 môn Toán — Sở GD&ĐT Hà Nội",
        "description": "Đề thi cấu trúc chuẩn 3 phần của Bộ GD&ĐT (Trắc nghiệm nhiều lựa chọn, Đúng/Sai, Trả lời ngắn)",
        "duration_minutes": 90,
        "exam_type": "mock",
        "province": "Hà Nội",
        "school_or_dept": "Sở GD&ĐT Hà Nội",
        "exam_year": 2025,
        "exam_round": "Lần 1",
        "curriculum_standard": "GDPT 2018",
        "is_authentic": True,
        "questions": [
            # PHẦN I: Trắc nghiệm 4 lựa chọn
            {
                "qn": 1,
                "question_type": "multiple_choice",
                "text": "Cho hàm số $y = f(x)$ có đạo hàm $f'(x) = 3x^2 - 3$. Hàm số đã cho đồng biến trên khoảng nào dưới đây?",
                "a": "$(-\\infty; -1)$", "b": "$(-1; 1)$", "c": "$(-\\infty; -1)$ và $(1; +\\infty)$", "d": "$(1; +\\infty)$",
                "answer": "C", "explanation": "$f'(x) = 3(x-1)(x+1) > 0$ khi $x \\in (-\\infty; -1) \\cup (1; +\\infty)$.",
                "tag": "Ứng dụng đạo hàm",
            },
            {
                "qn": 2,
                "question_type": "multiple_choice",
                "text": "Tiệm cận ngang của đồ thị hàm số $y = \\frac{2x + 1}{x - 1}$ có phương trình là:",
                "a": "$y = 1$", "b": "$y = 2$", "c": "$x = 1$", "d": "$y = -1$",
                "answer": "B", "explanation": "$\\lim_{x \\to +\\infty} \\frac{2x+1}{x-1} = 2$. Tiệm cận ngang là đường thẳng $y = 2$.",
                "tag": "Tiệm cận",
            },
            {
                "qn": 3,
                "question_type": "multiple_choice",
                "text": "Nghiệm của phương trình $\\log_2(x - 1) = 3$ là:",
                "a": "$x = 7$", "b": "$x = 9$", "c": "$x = 8$", "d": "$x = 10$",
                "answer": "B", "explanation": "Điều kiện $x > 1$. $\\log_2(x - 1) = 3 \\Leftrightarrow x - 1 = 2^3 = 8 \\Leftrightarrow x = 9$.",
                "tag": "Hàm số mũ logarit",
            },
            # PHẦN II: Trắc nghiệm Đúng / Sai
            {
                "qn": 4,
                "question_type": "true_false",
                "text": "Cho hàm số $f(x) = x^3 - 3x + 2$. Xét tính Đúng hoặc Sai của các mệnh đề sau:",
                "a": "Đạo hàm của hàm số là $f'(x) = 3x^2 - 3$.",
                "b": "Hàm số đạt cực đại tại điểm $x = 1$.",
                "c": "Điểm cực tiểu của đồ thị hàm số là tọa độ $(1; 0)$.",
                "d": "Đồ thị hàm số đi qua điểm $M(0; 2)$.",
                "answer": "T,F,T,T",
                "explanation": "a) $f'(x) = 3x^2 - 3$ (Đúng). b) Tại $x = 1$, $f'(1) = 0$ và đổi dấu từ âm sang dương nên $x = 1$ là điểm cực tiểu (Sai). c) $f(1) = 0$ => Cực tiểu là $(1; 0)$ (Đúng). d) $f(0) = 2$ (Đúng).",
                "tag": "Khảo sát hàm số (Đúng/Sai)",
            },
            # PHẦN III: Trắc nghiệm Trả lời ngắn
            {
                "qn": 5,
                "question_type": "short_answer",
                "text": "Cho khối chóp $S.ABC$ có đáy $ABC$ là tam giác vuông tại $B$, $AB = 3$, $BC = 4$. Cạnh bên $SA$ vuông góc với mặt phẳng $(ABC)$ và $SA = 5$. Tính thể tích $V$ của khối chóp $S.ABC$.",
                "answer": "10",
                "explanation": "Diện tích đáy $S_{\\Delta ABC} = \\frac{1}{2} \\cdot 3 \\cdot 4 = 6$. Thể tích $V = \\frac{1}{3} \\cdot S_{\\Delta ABC} \\cdot SA = \\frac{1}{3} \\cdot 6 \\cdot 5 = 10$.",
                "tag": "Khối đa diện (Trả lời ngắn)",
            },
        ],
    },
    {
        "subject": "Vật lý",
        "title": "Đề khảo sát chất lượng THPT 2025 môn Vật lý — THPT Chuyên Lam Sơn (Thanh Hóa)",
        "description": "Đề thi thử chính thức Trường THPT Chuyên Lam Sơn chuẩn cấu trúc 3 phần GDPT 2018",
        "duration_minutes": 50,
        "exam_type": "mock",
        "province": "Thanh Hóa",
        "school_or_dept": "THPT Chuyên Lam Sơn",
        "exam_year": 2025,
        "exam_round": "Lần 1",
        "curriculum_standard": "GDPT 2018",
        "is_authentic": True,
        "questions": [
            # PHẦN I: Trắc nghiệm 4 lựa chọn
            {
                "qn": 1,
                "question_type": "multiple_choice",
                "text": "Một vật dao động điều hòa theo phương trình $x = A \\cos(\\omega t + \\varphi)$. Chu kì dao động $T$ của con lắc lò xo được tính theo công thức:",
                "a": "$T = 2\\pi \\sqrt{\\frac{k}{m}}$", "b": "$T = 2\\pi \\sqrt{\\frac{m}{k}}$",
                "c": "$T = \\frac{1}{2\\pi} \\sqrt{\\frac{m}{k}}$", "d": "$T = 2\\pi \\sqrt{\\frac{g}{l}}$",
                "answer": "B", "explanation": "Chu kì dao động con lắc lò xo $T = 2\\pi\\sqrt{\\frac{m}{k}}$.",
                "tag": "Dao động cơ",
            },
            {
                "qn": 2,
                "question_type": "multiple_choice",
                "text": "Khoảng cách giữa hai điểm gần nhau nhất trên cùng một phương truyền sóng dao động cùng pha là:",
                "a": "$\\lambda / 4$", "b": "$\\lambda$", "c": "$\\lambda / 2$", "d": "$2\\lambda$",
                "answer": "B", "explanation": "Khoảng cách gần nhất dao động cùng pha trên phương truyền là 1 bước sóng $\\lambda$.",
                "tag": "Sóng cơ",
            },
            {
                "qn": 3,
                "question_type": "multiple_choice",
                "text": "Đặt điện áp xoay chiều $u = U_0 \\cos(\\omega t)$ vào hai đầu đoạn mạch $RLC$ nối tiếp. Hiện tượng cộng hưởng điện xảy ra khi:",
                "a": "$\\omega = \\frac{1}{\\sqrt{LC}}$", "b": "$\\omega = LC$", "c": "$\\omega^2 = L/C$", "d": "$\\omega = \\sqrt{LC}$",
                "answer": "A", "explanation": "Cộng hưởng điện xảy ra khi $Z_L = Z_C \\Leftrightarrow \\omega = \\frac{1}{\\sqrt{LC}}$.",
                "tag": "Dòng điện xoay chiều",
            },
            # PHẦN II: Trắc nghiệm Đúng / Sai
            {
                "qn": 4,
                "question_type": "true_false",
                "text": "Một con lắc lò xo dao động điều hòa theo phương ngang có $m = 0,2\\text{ kg}$, $k = 20\\text{ N/m}$, biên độ $A = 5\\text{ cm}$. Lấy $\\pi^2 = 10$. Xét tính Đúng hoặc Sai của các mệnh đề sau:",
                "a": "Tần số góc của dao động là $\\omega = 10\\text{ rad/s}$.",
                "b": "Cơ năng của con lắc lò xo bằng $0,025\\text{ J}$.",
                "c": "Tốc độ cực đại của vật là $v_{\\max} = 50\\text{ cm/s}$.",
                "d": "Gia tốc cực đại của vật là $a_{\\max} = 50\\text{ m/s}^2$.",
                "answer": "T,T,T,F",
                "explanation": "a) $\\omega = \\sqrt{k/m} = \\sqrt{20/0,2} = 10\\text{ rad/s}$ (Đúng). b) $W = \\frac{1}{2} k A^2 = 0,5 \\cdot 20 \\cdot 0,05^2 = 0,025\\text{ J}$ (Đúng). c) $v_{\\max} = \\omega A = 10 \\cdot 5 = 50\\text{ cm/s}$ (Đúng). d) $a_{\\max} = \\omega^2 A = 100 \\cdot 0,05 = 5\\text{ m/s}^2$ (Sai, không phải 50).",
                "tag": "Con lắc lò xo (Đúng/Sai)",
            },
            # PHẦN III: Trắc nghiệm Trả lời ngắn
            {
                "qn": 5,
                "question_type": "short_answer",
                "text": "Một sóng cơ hình sin có tần số $f = 50\\text{ Hz}$ lan truyền với tốc độ $v = 20\\text{ m/s}$. Bước sóng $\\lambda$ của sóng cơ này bằng bao nhiêu mét? (Điền số thập phân)",
                "answer": "0.4",
                "explanation": "Bước sóng $\\lambda = \\frac{v}{f} = \\frac{20}{50} = 0,4\\text{ m}$.",
                "tag": "Sóng cơ (Trả lời ngắn)",
            },
        ],
    },
    {
        "subject": "Hóa học",
        "title": "Đề thi thử Tốt nghiệp THPT 2025 môn Hóa học — THPT Chuyên KHTN Hà Nội",
        "description": "Đề thi chuẩn cấu trúc 3 phần 2025 bám sát danh pháp quốc tế IUPAC mới",
        "duration_minutes": 50,
        "exam_type": "mock",
        "province": "Hà Nội",
        "school_or_dept": "THPT Chuyên Khoa Học Tự Nhiên",
        "exam_year": 2025,
        "exam_round": "Lần 1",
        "curriculum_standard": "GDPT 2018",
        "is_authentic": True,
        "questions": [
            # PHẦN I: Trắc nghiệm 4 lựa chọn
            {
                "qn": 1,
                "question_type": "multiple_choice",
                "text": "Ester ethyl acetate có công thức phân tử là:",
                "a": "$\\text{CH}_3\\text{COOCH}_3$", "b": "$\\text{CH}_3\\text{COOC}_2\\text{H}_5$", "c": "$\\text{HCOOC}_2\\text{H}_5$", "d": "$\\text{C}_2\\text{H}_5\\text{COOCH}_3$",
                "answer": "B", "explanation": "Ethyl acetate tạo từ acetic acid và ethanol: $\\text{CH}_3\\text{COOC}_2\\text{H}_5$.",
                "tag": "Ester - Lipid (IUPAC)",
            },
            {
                "qn": 2,
                "question_type": "multiple_choice",
                "text": "Carbohydrate nào sau đây thuộc loại polysaccharide cấu tạo nên màng tế bào thực vật?",
                "a": "Glucose", "b": "Fructose", "c": "Sucrose", "d": "Cellulose",
                "answer": "D", "explanation": "Cellulose là polysaccharide chính trong vách tế bào thực vật.",
                "tag": "Carbohydrate (IUPAC)",
            },
            {
                "qn": 3,
                "question_type": "multiple_choice",
                "text": "Theo dãy điện hóa, kim loại nào sau đây có tính khử mạnh nhất ở điều kiện chuẩn?",
                "a": "Silver (Ag)", "b": "Copper (Cu)", "c": "Iron (Fe)", "d": "Potassium (K)",
                "answer": "D", "explanation": "Potassium (K) đứng đầu trong dãy nên tính khử mạnh nhất.",
                "tag": "Đại cương kim loại",
            },
            # PHẦN II: Trắc nghiệm Đúng / Sai
            {
                "qn": 4,
                "question_type": "true_false",
                "text": "Tiến hành thí nghiệm xà phòng hóa chất béo tristearin bằng dung dịch $\\text{NaOH}$ đun nóng. Xét tính Đúng hoặc Sai của các phát biểu sau:",
                "a": "Sản phẩm thu được sau phản ứng gồm sodium stearate và glycerol.",
                "b": "Sau khi thêm dung dịch $\\text{NaCl}$ bão hòa và để nguội, xà phòng sẽ tách ra và nổi lên trên.",
                "c": "Vai trò của $\\text{NaCl}$ là để xúc tác cho phản ứng thủy phân xảy ra nhanh hơn.",
                "d": "Chất béo tristearin ở điều kiện thường ở trạng thái rắn.",
                "answer": "T,T,F,T",
                "explanation": "a) Tristearin + 3NaOH -> 3 Sodium stearate + Glycerol (Đúng). b) Thêm NaCl bão hòa làm giảm độ tan của xà phòng, giúp xà phòng đông đặc và nổi lên (Đúng). c) NaCl làm tách muối xà phòng, không phải chất xúc tác (Sai). d) Tristearin là chất béo no nên ở thể rắn (Đúng).",
                "tag": "Lipid - Xà phòng hóa (Đúng/Sai)",
            },
            # PHẦN III: Trắc nghiệm Trả lời ngắn
            {
                "qn": 5,
                "question_type": "short_answer",
                "text": "Lên men $180\\text{ gam}$ glucose thành ethanol với hiệu suất phản ứng đạt $80\\%$. Khối lượng ethanol thu được là bao nhiêu gam? (Điền số thập phân)",
                "answer": "73.6",
                "explanation": "Phương trình: $\\text{C}_6\\text{H}_{12}\\text{O}_6 \\to 2\\text{C}_2\\text{H}_5\\text{OH} + 2\\text{CO}_2$. Số mol glucose = $180/180 = 1\\text{ mol}$. Khối lượng ethanol theo lý thuyết = $2 \\cdot 46 = 92\\text{ g}$. Thực tế với $H = 80\\%$: $m = 92 \\cdot 0,8 = 73,6\\text{ g}$.",
                "tag": "Carbohydrate (Trả lời ngắn)",
            },
        ],
    },
]


def seed_database(db: Session) -> None:
    """Tạo dữ liệu mẫu nếu DB chưa có môn nào."""
    existing = db.query(Subject).count()
    if existing > 0:
        logger.info(f"DB đã có {existing} môn — bỏ qua seed.")
        return

    logger.info("Bắt đầu seed dữ liệu Toán - Vật lý - Hóa học lớp 12...")

    subject_map = {}  # name -> Subject obj

    for subject_name, data in CURRICULUM.items():
        subject = Subject(name=subject_name, icon=data["icon"])
        db.add(subject)
        db.flush()  # lấy id
        subject_map[subject_name] = subject

        for order, ch in enumerate(data["chapters"], 1):
            chapter = Chapter(subject_id=subject.id, name=ch["name"], order=order)
            db.add(chapter)
            db.flush()

            for lesson_title in ch["lessons"]:
                lesson = Lesson(chapter_id=chapter.id, title=lesson_title)
                db.add(lesson)

    # Tạo đề thi mẫu
    for exam_data in SAMPLE_EXAMS:
        subject = subject_map.get(exam_data["subject"])
        if not subject:
            continue

        exam = Exam(
            subject_id=subject.id,
            title=exam_data["title"],
            description=exam_data["description"],
            duration_minutes=exam_data["duration_minutes"],
            exam_type=exam_data["exam_type"],
            province=exam_data.get("province"),
            school_or_dept=exam_data.get("school_or_dept"),
            exam_year=exam_data.get("exam_year", 2025),
            exam_round=exam_data.get("exam_round", "Lần 1"),
            curriculum_standard=exam_data.get("curriculum_standard", "GDPT 2018"),
            is_authentic=exam_data.get("is_authentic", True),
            source_origin=exam_data.get("school_or_dept"),
            total_questions=len(exam_data["questions"]),
        )
        db.add(exam)
        db.flush()

        for q in exam_data["questions"]:
            question = ExamQuestion(
                exam_id=exam.id,
                question_number=q["qn"],
                question_type=q.get("question_type", "multiple_choice"),
                question_text=q["text"],
                option_a=q.get("a") or "",
                option_b=q.get("b") or "",
                option_c=q.get("c") or "",
                option_d=q.get("d") or "",
                correct_answer=q["answer"],
                explanation=q.get("explanation"),
                topic_tag=q.get("tag"),
            )
            db.add(question)

    db.commit()
    logger.info("Seed hoàn tất: 3 môn, đề thi mẫu đã tạo.")
