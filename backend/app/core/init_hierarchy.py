"""
Khởi tạo và đồng bộ hệ thống phân cấp địa lý 3 cấp:
Miền (Bắc, Trung, Nam) -> Tỉnh / Thành phố (63 tỉnh) -> Trường THPT / Sở GD&ĐT -> Phân loại đề thi.
"""
import logging
import sqlite3
from sqlalchemy.orm import Session
from app.core.database import DB_PATH, engine, Base
from app.models.models import Region, Province, School, Exam

logger = logging.getLogger("studyapp.hierarchy")

REGIONS_DATA = [
    {
        "name": "Bắc",
        "code": "bac",
        "description": "Các tỉnh và trường THPT khu vực phía Bắc (Đồng bằng sông Hồng, Tây Bắc, Đông Bắc)",
        "provinces": [
            ("Hà Nội", "ha_noi"),
            ("Hải Phòng", "hai_phong"),
            ("Quảng Ninh", "quang_ninh"),
            ("Bắc Ninh", "bac_ninh"),
            ("Hà Nam", "ha_nam"),
            ("Hải Dương", "hai_duong"),
            ("Hưng Yên", "hung_yen"),
            ("Nam Định", "nam_dinh"),
            ("Ninh Bình", "ninh_binh"),
            ("Thái Bình", "thai_binh"),
            ("Vĩnh Phúc", "vinh_phuc"),
            ("Hà Giang", "ha_giang"),
            ("Cao Bằng", "cao_bang"),
            ("Bắc Kạn", "bac_kan"),
            ("Lạng Sơn", "lang_son"),
            ("Tuyên Quang", "tuyen_quang"),
            ("Thái Nguyên", "thai_nguyen"),
            ("Phú Thọ", "phu_tho"),
            ("Bắc Giang", "bac_giang"),
            ("Lào Cai", "lao_cai"),
            ("Yên Bái", "yen_bai"),
            ("Điện Biên", "dien_bien"),
            ("Lai Châu", "lai_chau"),
            ("Sơn La", "son_la"),
            ("Hòa Bình", "hoa_binh"),
        ],
    },
    {
        "name": "Trung",
        "code": "trung",
        "description": "Các tỉnh và trường THPT khu vực miền Trung và Tây Nguyên (Bắc Trung Bộ, Nam Trung Bộ, Tây Nguyên)",
        "provinces": [
            ("Thanh Hóa", "thanh_hoa"),
            ("Nghệ An", "nghe_an"),
            ("Hà Tĩnh", "ha_tinh"),
            ("Quảng Bình", "quang_binh"),
            ("Quảng Trị", "quang_tri"),
            ("Thừa Thiên Huế", "thua_thien_hue"),
            ("Đà Nẵng", "da_nang"),
            ("Quảng Nam", "quang_nam"),
            ("Quảng Ngãi", "quang_ngai"),
            ("Bình Định", "binh_dinh"),
            ("Phú Yên", "phu_yen"),
            ("Khánh Hòa", "khanh_hoa"),
            ("Ninh Thuận", "ninh_thuan"),
            ("Bình Thuận", "binh_thuan"),
            ("Kon Tum", "kon_tum"),
            ("Gia Lai", "gia_lai"),
            ("Đắk Lắk", "dak_lak"),
            ("Đắk Nông", "dak_nong"),
            ("Lâm Đồng", "lam_dong"),
        ],
    },
    {
        "name": "Nam",
        "code": "nam",
        "description": "Các tỉnh và trường THPT khu vực phía Nam (Đông Nam Bộ và Đồng bằng sông Cửu Long)",
        "provinces": [
            ("TP. Hồ Chí Minh", "tp_ho_chi_minh"),
            ("Bà Rịa - Vũng Tàu", "ba_ria_vung_tau"),
            ("Bình Dương", "binh_duong"),
            ("Bình Phước", "binh_phuoc"),
            ("Đồng Nai", "dong_nai"),
            ("Tây Ninh", "tay_ninh"),
            ("An Giang", "an_giang"),
            ("Bạc Liêu", "bac_lieu"),
            ("Bến Tre", "ben_tre"),
            ("Cà Mau", "ca_mau"),
            ("Cần Thơ", "can_tho"),
            ("Đồng Tháp", "dong_thap"),
            ("Hậu Giang", "hau_giang"),
            ("Kiên Giang", "kien_giang"),
            ("Long An", "long_an"),
            ("Sóc Trăng", "soc_trang"),
            ("Tiền Giang", "tien_giang"),
            ("Trà Vinh", "tra_vinh"),
            ("Vĩnh Long", "vinh_long"),
        ],
    },
]


def migrate_exam_table():
    """Bổ sung các cột phân cấp vào bảng exams nếu chưa có."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(exams)")
    columns = [row[1] for row in cur.fetchall()]

    if "school_id" not in columns:
        logger.info("Migrating SQLite: thêm cột school_id vào bảng exams")
        cur.execute("ALTER TABLE exams ADD COLUMN school_id INTEGER REFERENCES schools(id)")

    if "exam_category" not in columns:
        logger.info("Migrating SQLite: thêm cột exam_category vào bảng exams")
        cur.execute("ALTER TABLE exams ADD COLUMN exam_category VARCHAR(50) DEFAULT 'mock'")

    if "semester" not in columns:
        logger.info("Migrating SQLite: thêm cột semester vào bảng exams")
        cur.execute("ALTER TABLE exams ADD COLUMN semester VARCHAR(20) DEFAULT 'HK1'")

    conn.commit()
    conn.close()


def seed_hierarchy_data(db: Session):
    """Seed 3 Miền và 63 Tỉnh Thành."""
    # 1. Tạo bảng nếu chưa có
    Base.metadata.create_all(bind=engine)
    migrate_exam_table()

    # 2. Seed Miền & Tỉnh
    existing_regions = db.query(Region).count()
    if existing_regions == 0:
        logger.info("Bắt đầu nạp 3 Miền và 63 Tỉnh Thành vào Hệ thống phân cấp...")
        for r_data in REGIONS_DATA:
            reg = Region(name=r_data["name"], code=r_data["code"], description=r_data["description"])
            db.add(reg)
            db.flush()

            for p_name, p_code in r_data["provinces"]:
                prov = Province(region_id=reg.id, name=p_name, code=p_code)
                db.add(prov)

        db.commit()
        logger.info("Đã nạp thành công 3 Miền và 63 Tỉnh Thành!")

    # 3. Liên kết các đề thi hiện có vào trường và tỉnh tương ứng
    exams = db.query(Exam).all()
    for ex in exams:
        if not ex.school_id and ex.province:
            # Tìm province
            p_name = ex.province.strip()
            prov = db.query(Province).filter(Province.name.ilike(f"%{p_name}%")).first()
            if prov:
                s_name = (ex.school_or_dept or f"Sở GD&ĐT {prov.name}").strip()
                school = db.query(School).filter(School.province_id == prov.id, School.name == s_name).first()
                if not school:
                    s_type = "dept" if "sở" in s_name.lower() else "thpt"
                    school = School(province_id=prov.id, name=s_name, school_type=s_type)
                    db.add(school)
                    db.flush()
                ex.school_id = school.id
                if not ex.exam_category:
                    ex.exam_category = "mock"
    db.commit()
