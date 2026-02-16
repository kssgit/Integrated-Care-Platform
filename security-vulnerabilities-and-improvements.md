# 서울케어플러스 보안 취약점 분석 및 개선 방안

## 📋 목차
1. [현재 보안 상태 평가](#1-현재-보안-상태-평가)
2. [식별된 보안 취약점](#2-식별된-보안-취약점)
3. [보안 아키텍처 설계](#3-보안-아키텍처-설계)
4. [개인정보보호법 준수](#4-개인정보보호법-준수)
5. [보안 구현 가이드](#5-보안-구현-가이드)
6. [보안 테스트 및 감사](#6-보안-테스트-및-감사)

---

## 1. 현재 보안 상태 평가

### 1.1 기존 시스템의 보안 문제점

**❌ Critical Issues (즉시 해결 필요)**:

1. **인증/인가 시스템 부재**
   - JWT 토큰 검증 로직 없음
   - API 엔드포인트 접근 제어 없음
   - 세션 관리 미구현

2. **개인정보 암호화 미적용**
   - 전화번호, 주민등록번호 평문 저장
   - 의료 정보 비식별화 미처리
   - 데이터베이스 암호화 없음

3. **API 보안 부재**
   - Rate Limiting 없음
   - CORS 설정 미흡
   - API 키 관리 시스템 없음

4. **로깅 및 감사 추적 부족**
   - 접근 로그 미수집
   - 민감 정보 접근 기록 없음
   - 이상 행위 탐지 시스템 없음

**⚠️ High Priority Issues**:

5. **파일 업로드 취약점**
   - 파일 타입 검증 없음
   - 파일 크기 제한 없음
   - 악성 파일 스캔 없음

6. **SQL Injection 취약점**
   - ORM 미사용 시 직접 쿼리 가능성
   - Input Sanitization 부족

7. **XSS (Cross-Site Scripting) 취약점**
   - 사용자 입력 검증 부족
   - Output Encoding 미적용

---

## 2. 식별된 보안 취약점

### 2.1 인증/인가 (Authentication & Authorization)

**현재 문제**:
```python
# ❌ 취약한 코드 예시
@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: str):
    # 인증 체크 없음!
    user = await db.fetch_one("SELECT * FROM users WHERE user_id = :user_id", {"user_id": user_id})
    return user
```

**개선 방안**:
```python
# ✅ 보안 강화된 코드
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """JWT 토큰 검증 및 현재 사용자 추출"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # 토큰 블랙리스트 체크
        if await is_token_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

@app.get("/api/v1/users/{user_id}")
async def get_user(
    user_id: str,
    current_user_id: str = Depends(get_current_user)
):
    # 권한 체크: 본인만 조회 가능
    if user_id != current_user_id:
        # 관리자인 경우 허용
        if not await is_admin(current_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this resource"
            )
    
    user = await db.fetch_one(
        "SELECT * FROM users WHERE user_id = :user_id",
        {"user_id": user_id}
    )
    
    # 민감 정보 제거
    return sanitize_user_data(user)
```

### 2.2 개인정보 암호화

**암호화 전략**:

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64
import os

class DataEncryption:
    """개인정보 암호화/복호화"""
    
    def __init__(self):
        # 환경 변수에서 키 로드
        self.master_key = os.getenv("ENCRYPTION_MASTER_KEY")
        
        if not self.master_key:
            raise ValueError("ENCRYPTION_MASTER_KEY not set")
        
        # 키 파생 함수 (KDF)
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'seoul_care_plus_salt',  # 실제로는 시크릿에서 로드
            iterations=100000
        )
        
        key = base64.urlsafe_b64encode(
            kdf.derive(self.master_key.encode())
        )
        
        self.cipher = Fernet(key)
    
    def encrypt_field(self, plaintext: str) -> str:
        """필드 암호화"""
        if not plaintext:
            return None
        
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_field(self, ciphertext: str) -> str:
        """필드 복호화"""
        if not ciphertext:
            return None
        
        try:
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def encrypt_phone(self, phone: str) -> str:
        """전화번호 암호화 (포맷 유지)"""
        # 010-1234-5678 → E(010)-E(1234)-E(5678)
        parts = phone.split('-')
        encrypted_parts = [self.encrypt_field(part) for part in parts]
        return '-'.join(encrypted_parts)
    
    def hash_for_search(self, value: str) -> str:
        """검색용 해시 (일방향)"""
        import hashlib
        
        # HMAC-SHA256 사용
        h = hashlib.sha256()
        h.update(self.master_key.encode())
        h.update(value.encode())
        
        return h.hexdigest()

# 사용 예시
encryption = DataEncryption()

# 사용자 등록 시
user_data = {
    'email': 'user@example.com',
    'phone': '010-1234-5678',
    'name': '홍길동'
}

encrypted_data = {
    'email': user_data['email'],  # 이메일은 평문 (로그인용)
    'phone_encrypted': encryption.encrypt_phone(user_data['phone']),
    'phone_hash': encryption.hash_for_search(user_data['phone']),  # 검색용
    'name_encrypted': encryption.encrypt_field(user_data['name'])
}

# 전화번호로 검색 시
search_hash = encryption.hash_for_search('010-1234-5678')
query = "SELECT * FROM users WHERE phone_hash = :hash"
```

**암호화 필드 목록**:

```python
ENCRYPTION_REQUIRED_FIELDS = {
    'users': [
        'phone',              # 전화번호
        'real_name',          # 실명
        'resident_number',    # 주민등록번호 (사용 최소화)
        'address_detail',     # 상세 주소
    ],
    'care_records': [
        'medical_history',    # 질환 이력
        'medication',         # 투약 정보
        'health_notes',       # 건강 메모
    ],
    'payments': [
        'card_number',        # 카드 번호 (토큰화 권장)
        'bank_account',       # 계좌 번호
    ]
}
```

### 2.3 SQL Injection 방어

**❌ 취약한 코드**:
```python
# 절대 하지 마세요!
@app.get("/api/v1/facilities/search")
async def search_facilities(name: str):
    query = f"SELECT * FROM facilities WHERE name LIKE '%{name}%'"
    # SQL Injection 취약!
    results = await db.fetch_all(query)
    return results
```

**✅ 안전한 코드**:
```python
# Prepared Statement 사용
@app.get("/api/v1/facilities/search")
async def search_facilities(name: str):
    # 입력 검증
    if not validate_search_input(name):
        raise HTTPException(400, "Invalid search input")
    
    # Parameterized Query
    query = "SELECT * FROM facilities WHERE name ILIKE :name"
    results = await db.fetch_all(
        query,
        {"name": f"%{name}%"}
    )
    
    return results

def validate_search_input(text: str) -> bool:
    """검색 입력 검증"""
    # 길이 체크
    if len(text) > 100:
        return False
    
    # 특수 문자 체크
    import re
    if re.search(r'[;\'"\\]', text):
        return False
    
    return True
```

### 2.4 XSS (Cross-Site Scripting) 방어

**출력 인코딩**:
```python
import html
from markupsafe import escape

def sanitize_output(text: str) -> str:
    """HTML 출력 시 XSS 방어"""
    if not text:
        return ""
    
    # HTML 엔티티 인코딩
    return html.escape(text)

def sanitize_review_content(content: str) -> str:
    """리뷰 콘텐츠 정제"""
    import bleach
    
    # 허용된 HTML 태그만
    allowed_tags = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li']
    allowed_attrs = {}
    
    cleaned = bleach.clean(
        content,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True
    )
    
    return cleaned

# API 응답 시 적용
@app.get("/api/v1/reviews/{review_id}")
async def get_review(review_id: str):
    review = await db.fetch_one(
        "SELECT * FROM reviews WHERE review_id = :id",
        {"id": review_id}
    )
    
    # 출력 시 sanitize
    return {
        "review_id": review["review_id"],
        "title": sanitize_output(review["title"]),
        "content": sanitize_review_content(review["content"]),
        "rating": review["rating"]
    }
```

### 2.5 Rate Limiting

**API Rate Limiting 구현**:
```python
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis

# Redis 연결
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Limiter 생성
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 전역 Rate Limit
@app.get("/api/v1/facilities")
@limiter.limit("100/minute")  # 분당 100회
async def get_facilities(request: Request):
    ...

# 인증된 사용자는 더 높은 한도
@app.post("/api/v1/reviews")
@limiter.limit("10/minute")  # 분당 10회
async def create_review(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    ...

# 로그인 시도 제한 (IP 기반)
@app.post("/api/v1/auth/login")
@limiter.limit("5/5minutes")  # 5분에 5회
async def login(request: Request, credentials: LoginCredentials):
    ...

# Custom Rate Limiter (토큰 버킷 알고리즘)
class TokenBucketRateLimiter:
    def __init__(self, capacity: int, refill_rate: float):
        """
        capacity: 버킷 용량
        refill_rate: 초당 토큰 충전 속도
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
    
    async def is_allowed(self, key: str) -> bool:
        """요청 허용 여부 확인"""
        current_time = time.time()
        
        # Redis에서 버킷 상태 가져오기
        bucket_key = f"rate_limit:token_bucket:{key}"
        bucket_data = redis_client.hgetall(bucket_key)
        
        if not bucket_data:
            # 새 버킷 생성
            tokens = self.capacity - 1
            last_refill = current_time
        else:
            tokens = float(bucket_data[b'tokens'])
            last_refill = float(bucket_data[b'last_refill'])
            
            # 토큰 충전
            time_passed = current_time - last_refill
            tokens_to_add = time_passed * self.refill_rate
            tokens = min(self.capacity, tokens + tokens_to_add)
        
        # 요청 처리
        if tokens >= 1:
            tokens -= 1
            
            # 상태 저장
            redis_client.hset(bucket_key, mapping={
                'tokens': tokens,
                'last_refill': current_time
            })
            redis_client.expire(bucket_key, 3600)  # 1시간 TTL
            
            return True
        else:
            return False
```

### 2.6 CORS (Cross-Origin Resource Sharing)

**안전한 CORS 설정**:
```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Production 환경
if os.getenv("ENVIRONMENT") == "production":
    allowed_origins = [
        "https://www.seoulcareplus.com",
        "https://app.seoulcareplus.com",
        "https://admin.seoulcareplus.com"
    ]
else:
    # Development 환경
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600
)
```

### 2.7 파일 업로드 보안

**안전한 파일 업로드**:
```python
from fastapi import UploadFile, File, HTTPException
import magic
import hashlib
from PIL import Image
import io

# 허용된 MIME 타입
ALLOWED_MIME_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/webp': ['.webp'],
    'application/pdf': ['.pdf']
}

# 최대 파일 크기 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

async def validate_and_process_file(
    file: UploadFile
) -> dict:
    """파일 검증 및 처리"""
    
    # 1. 파일 크기 체크
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            400,
            f"File size exceeds limit ({MAX_FILE_SIZE/1024/1024}MB)"
        )
    
    # 2. MIME 타입 검증 (magic number 기반)
    mime_type = magic.from_buffer(contents, mime=True)
    
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            400,
            f"File type not allowed: {mime_type}"
        )
    
    # 3. 파일 확장자 검증
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = ALLOWED_MIME_TYPES[mime_type]
    
    if file_ext not in allowed_exts:
        raise HTTPException(
            400,
            "File extension does not match content type"
        )
    
    # 4. 이미지인 경우 추가 검증
    if mime_type.startswith('image/'):
        try:
            image = Image.open(io.BytesIO(contents))
            
            # 이미지 형식 재확인
            if image.format.lower() not in ['jpeg', 'jpg', 'png', 'webp']:
                raise HTTPException(400, "Invalid image format")
            
            # EXIF 데이터 제거 (메타데이터 스트립)
            image_without_exif = Image.new(image.mode, image.size)
            image_without_exif.putdata(list(image.getdata()))
            
            # 재인코딩
            output = io.BytesIO()
            image_without_exif.save(output, format=image.format)
            contents = output.getvalue()
            
        except Exception as e:
            raise HTTPException(400, f"Invalid image file: {str(e)}")
    
    # 5. 바이러스 스캔 (ClamAV)
    if not await scan_for_malware(contents):
        raise HTTPException(400, "File contains malicious content")
    
    # 6. 파일 해시 계산 (중복 방지)
    file_hash = hashlib.sha256(contents).hexdigest()
    
    # 7. 안전한 파일명 생성
    safe_filename = f"{file_hash}{file_ext}"
    
    return {
        'filename': safe_filename,
        'original_filename': file.filename,
        'mime_type': mime_type,
        'file_size': file_size,
        'file_hash': file_hash,
        'contents': contents
    }

async def scan_for_malware(file_contents: bytes) -> bool:
    """ClamAV를 사용한 악성코드 스캔"""
    import pyclamd
    
    try:
        cd = pyclamd.ClamdUnixSocket()
        
        # 파일 스캔
        scan_result = cd.scan_stream(file_contents)
        
        if scan_result is None:
            # 악성코드 없음
            return True
        else:
            # 악성코드 발견
            logger.warning(f"Malware detected: {scan_result}")
            return False
            
    except Exception as e:
        logger.error(f"Malware scan failed: {e}")
        # 스캔 실패 시 보수적으로 거부
        return False

# API 엔드포인트
@app.post("/api/v1/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    # 파일 검증
    validated_file = await validate_and_process_file(file)
    
    # S3/CloudFlare R2에 업로드
    file_url = await upload_to_storage(
        validated_file['contents'],
        validated_file['filename']
    )
    
    # DB에 메타데이터 저장
    await db.execute(
        """
        INSERT INTO uploaded_files 
        (file_id, user_id, filename, original_filename, mime_type, file_size, file_hash, file_url)
        VALUES (:file_id, :user_id, :filename, :original_filename, :mime_type, :file_size, :file_hash, :file_url)
        """,
        {
            'file_id': str(uuid.uuid4()),
            'user_id': current_user,
            'filename': validated_file['filename'],
            'original_filename': validated_file['original_filename'],
            'mime_type': validated_file['mime_type'],
            'file_size': validated_file['file_size'],
            'file_hash': validated_file['file_hash'],
            'file_url': file_url
        }
    )
    
    return {
        'file_url': file_url,
        'file_hash': validated_file['file_hash']
    }
```

---

## 3. 보안 아키텍처 설계

### 3.1 Defense in Depth (다층 방어)

```
┌─────────────────────────────────────────────────────────────┐
│                Layer 1: Network Security                     │
│  - WAF (Web Application Firewall)                           │
│  - DDoS Protection (Cloudflare)                             │
│  - IP Whitelisting (Admin APIs)                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                Layer 2: API Gateway Security                 │
│  - Rate Limiting                                            │
│  - JWT Validation                                           │
│  - API Key Management                                       │
│  - Request/Response Logging                                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│            Layer 3: Application Security                     │
│  - Input Validation                                         │
│  - Output Encoding                                          │
│  - Session Management                                       │
│  - CSRF Protection                                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              Layer 4: Data Security                          │
│  - Encryption at Rest (AES-256)                             │
│  - Encryption in Transit (TLS 1.3)                          │
│  - Field-Level Encryption                                   │
│  - Database Access Control                                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│          Layer 5: Infrastructure Security                    │
│  - Container Security                                       │
│  - Network Segmentation                                     │
│  - Secrets Management (Vault)                               │
│  - Security Monitoring                                      │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Zero Trust Architecture

**핵심 원칙**:
1. **절대 신뢰하지 말고, 항상 검증하라**
2. **최소 권한 원칙 (Principle of Least Privilege)**
3. **네트워크 위치가 신뢰를 의미하지 않음**

**구현**:
```python
# 모든 요청에 대해 인증/인가 검증
class ZeroTrustMiddleware:
    async def __call__(self, request: Request, call_next):
        # 1. 인증 확인
        if not await verify_authentication(request):
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthenticated"}
            )
        
        # 2. 권한 확인
        if not await verify_authorization(request):
            return JSONResponse(
                status_code=403,
                content={"detail": "Unauthorized"}
            )
        
        # 3. 요청 컨텍스트 로깅
        await log_request_context(request)
        
        # 4. 요청 처리
        response = await call_next(request)
        
        # 5. 응답 로깅
        await log_response(request, response)
        
        return response
```

### 3.3 Secrets Management

**HashiCorp Vault 사용**:
```python
import hvac

class SecretsManager:
    def __init__(self):
        self.client = hvac.Client(
            url=os.getenv('VAULT_ADDR'),
            token=os.getenv('VAULT_TOKEN')
        )
    
    def get_secret(self, path: str) -> dict:
        """시크릿 가져오기"""
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path
            )
            
            return response['data']['data']
        except Exception as e:
            logger.error(f"Failed to retrieve secret: {e}")
            raise
    
    def get_db_credentials(self) -> dict:
        """DB 접속 정보 가져오기"""
        return self.get_secret('database/postgresql')
    
    def get_api_keys(self) -> dict:
        """외부 API 키 가져오기"""
        return self.get_secret('api-keys/external')
    
    def rotate_secret(self, path: str, new_value: dict):
        """시크릿 갱신"""
        self.client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret=new_value
        )

# 사용 예시
secrets = SecretsManager()

# DB 연결 시
db_creds = secrets.get_db_credentials()
DATABASE_URL = f"postgresql://{db_creds['username']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"

# 외부 API 호출 시
api_keys = secrets.get_api_keys()
NAVER_OCR_KEY = api_keys['naver_clova_ocr']
```

---

## 4. 개인정보보호법 준수

### 4.1 법적 요구사항

**개인정보보호법 제24조의2 (가명처리)**:
- 통계 작성, 과학적 연구, 공익적 기록보존 목적
- 추가 정보 없이는 특정 개인 식별 불가

**정보통신망법 제70조 (명예훼손 등)**:
- 권리 침해 정보에 대한 삭제 요청 시 임시 조치 (30일)

### 4.2 가명처리 (De-identification)

```python
import hashlib
import uuid

class DataDeidentifier:
    """개인정보 가명처리"""
    
    def __init__(self, salt: str):
        self.salt = salt
    
    def pseudonymize(self, identifier: str) -> str:
        """가명 처리 (복원 가능)"""
        # HMAC-SHA256
        h = hashlib.sha256()
        h.update(self.salt.encode())
        h.update(identifier.encode())
        
        return h.hexdigest()
    
    def anonymize_for_analytics(self, user_data: dict) -> dict:
        """분석용 익명화"""
        return {
            'user_id_hash': self.pseudonymize(user_data['user_id']),
            'age_group': self.get_age_group(user_data['age']),
            'district': user_data['district'],  # 구 단위는 유지
            'user_type': user_data['user_type'],
            'registration_month': user_data['created_at'].strftime('%Y-%m')
        }
    
    def get_age_group(self, age: int) -> str:
        """연령대 그룹화"""
        if age < 20:
            return '10대'
        elif age < 30:
            return '20대'
        elif age < 40:
            return '30대'
        elif age < 50:
            return '40대'
        elif age < 60:
            return '50대'
        else:
            return '60대 이상'
    
    def mask_phone(self, phone: str) -> str:
        """전화번호 마스킹"""
        # 010-1234-5678 → 010-****-5678
        parts = phone.split('-')
        if len(parts) == 3:
            return f"{parts[0]}-****-{parts[2]}"
        return phone
    
    def mask_email(self, email: str) -> str:
        """이메일 마스킹"""
        # user@example.com → u***@example.com
        username, domain = email.split('@')
        masked_username = username[0] + '***'
        return f"{masked_username}@{domain}"
```

### 4.3 데이터 최소화

**수집 최소화**:
```python
# 필수 필드만 수집
USER_REQUIRED_FIELDS = [
    'email',       # 로그인용
    'password',    # 인증용
    'phone',       # 본인 확인용
    'user_type'    # 서비스 구분용
]

USER_OPTIONAL_FIELDS = [
    'name',        # 선택
    'birth_date',  # 선택 (만 나이 계산용)
    'address'      # 선택 (위치 기반 서비스용)
]

# 주민등록번호는 수집하지 않음!
# 대신 본인 확인은 휴대폰 인증으로 대체
```

**보유 기간 제한**:
```python
# 데이터 보유 정책
DATA_RETENTION_POLICY = {
    'user_accounts': {
        'active': None,  # 계정 활성 시 무제한
        'inactive': 365 * 3,  # 3년 미접속 시 삭제 안내
        'deleted': 30  # 탈퇴 후 30일간 복구 가능
    },
    'care_records': {
        'retention_days': 365 * 5  # 5년 보관
    },
    'access_logs': {
        'retention_days': 365  # 1년 보관
    },
    'payment_records': {
        'retention_days': 365 * 5  # 5년 보관 (법적 요구)
    }
}

# 자동 삭제 스케줄러
async def cleanup_expired_data():
    """만료된 데이터 자동 삭제"""
    
    # 1. 장기 미접속 사용자
    inactive_threshold = datetime.now() - timedelta(
        days=DATA_RETENTION_POLICY['user_accounts']['inactive']
    )
    
    inactive_users = await db.fetch_all(
        """
        SELECT user_id, email
        FROM users
        WHERE last_login_at < :threshold
        AND deletion_notified_at IS NULL
        """,
        {"threshold": inactive_threshold}
    )
    
    for user in inactive_users:
        # 삭제 안내 이메일 발송
        await send_deletion_notice(user['email'])
        
        # 안내 발송 기록
        await db.execute(
            "UPDATE users SET deletion_notified_at = NOW() WHERE user_id = :user_id",
            {"user_id": user['user_id']}
        )
    
    # 2. 안내 후 30일 경과 시 삭제
    deletion_threshold = datetime.now() - timedelta(days=30)
    
    await db.execute(
        """
        UPDATE users
        SET deleted_at = NOW(),
            email = CONCAT('deleted_', user_id, '@deleted.local'),
            phone_encrypted = NULL
        WHERE deletion_notified_at < :threshold
        AND deleted_at IS NULL
        """,
        {"threshold": deletion_threshold}
    )
    
    # 3. 케어 기록 만료
    care_record_threshold = datetime.now() - timedelta(
        days=DATA_RETENTION_POLICY['care_records']['retention_days']
    )
    
    await db.execute(
        "DELETE FROM care_records WHERE recorded_at < :threshold",
        {"threshold": care_record_threshold}
    )
    
    # 4. 접근 로그 만료
    log_threshold = datetime.now() - timedelta(
        days=DATA_RETENTION_POLICY['access_logs']['retention_days']
    )
    
    await db.execute(
        "DELETE FROM access_logs WHERE created_at < :threshold",
        {"threshold": log_threshold}
    )
```

### 4.4 접근 제어 및 감사 로그

```python
# 민감 정보 접근 로깅
async def log_sensitive_data_access(
    user_id: str,
    resource_type: str,
    resource_id: str,
    action: str,
    ip_address: str
):
    """민감 정보 접근 기록"""
    
    await db.execute(
        """
        INSERT INTO audit_logs 
        (user_id, resource_type, resource_id, action, ip_address, accessed_at)
        VALUES (:user_id, :resource_type, :resource_id, :action, :ip_address, NOW())
        """,
        {
            'user_id': user_id,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'action': action,
            'ip_address': ip_address
        }
    )
    
    # 이상 행위 탐지
    await detect_anomalous_access(user_id)

# API에 적용
@app.get("/api/v1/users/{user_id}/medical-records")
async def get_medical_records(
    user_id: str,
    current_user: str = Depends(get_current_user),
    request: Request
):
    # 권한 체크
    if user_id != current_user and not await is_authorized_caregiver(current_user, user_id):
        raise HTTPException(403, "Not authorized")
    
    # 접근 로깅
    await log_sensitive_data_access(
        user_id=current_user,
        resource_type='medical_records',
        resource_id=user_id,
        action='read',
        ip_address=request.client.host
    )
    
    # 데이터 조회
    records = await db.fetch_all(
        "SELECT * FROM medical_records WHERE user_id = :user_id",
        {"user_id": user_id}
    )
    
    return records
```

---

## 5. 보안 구현 가이드

### 5.1 환경 변수 관리

**.env.example**:
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/seoul_care_plus
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-here-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption
ENCRYPTION_MASTER_KEY=your-master-key-here-change-in-production

# External APIs
NAVER_CLOVA_OCR_API_KEY=your-api-key
GOOGLE_VISION_API_KEY=your-api-key
TOSS_PAYMENTS_SECRET_KEY=your-secret-key

# AWS
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=seoul-care-plus-uploads

# Monitoring
SENTRY_DSN=https://your-sentry-dsn

# Environment
ENVIRONMENT=development  # development, staging, production
DEBUG=false
```

**환경 변수 로딩**:
```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str
    database_pool_size: int = 20
    
    # Redis
    redis_url: str
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    
    # Encryption
    encryption_master_key: str
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# 사용
settings = get_settings()
```

### 5.2 로깅 및 모니터링

**구조화된 로깅**:
```python
import structlog
import logging.config

# 로깅 설정
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': structlog.stdlib.ProcessorFormatter,
            'processor': structlog.processors.JSONRenderer(),
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
    },
}

logging.config.dictConfig(LOGGING_CONFIG)

# Structlog 설정
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# 사용 예시
logger.info(
    "user_logged_in",
    user_id="550e8400-e29b-41d4-a716-446655440000",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0..."
)

logger.error(
    "database_connection_failed",
    error="Connection timeout",
    database="postgresql",
    host="localhost"
)
```

**보안 이벤트 모니터링**:
```python
# 의심스러운 활동 탐지
class SecurityMonitor:
    def __init__(self):
        self.redis_client = redis.Redis()
    
    async def detect_brute_force(self, user_id: str, ip_address: str):
        """무차별 대입 공격 탐지"""
        key = f"failed_logins:{ip_address}"
        
        failed_count = self.redis_client.incr(key)
        self.redis_client.expire(key, 300)  # 5분 TTL
        
        if failed_count >= 5:
            await self.alert_security_team(
                event_type="brute_force_attempt",
                ip_address=ip_address,
                user_id=user_id
            )
            
            # IP 차단
            await self.block_ip(ip_address, duration=3600)
    
    async def detect_credential_stuffing(self, ip_address: str):
        """credential stuffing 탐지"""
        key = f"login_attempts:{ip_address}"
        
        attempts = self.redis_client.incr(key)
        self.redis_client.expire(key, 60)  # 1분 TTL
        
        if attempts >= 10:
            await self.alert_security_team(
                event_type="credential_stuffing",
                ip_address=ip_address
            )
            
            # IP 차단
            await self.block_ip(ip_address, duration=7200)
    
    async def detect_data_exfiltration(self, user_id: str):
        """대량 데이터 유출 시도 탐지"""
        key = f"api_calls:{user_id}"
        
        call_count = self.redis_client.incr(key)
        self.redis_client.expire(key, 60)  # 1분 TTL
        
        if call_count >= 100:
            await self.alert_security_team(
                event_type="potential_data_exfiltration",
                user_id=user_id
            )
            
            # 사용자 임시 차단
            await self.suspend_user(user_id, duration=3600)
```

---

## 6. 보안 테스트 및 감사

### 6.1 보안 테스트 체크리스트

```python
# tests/security/test_authentication.py
import pytest

class TestAuthentication:
    """인증 보안 테스트"""
    
    async def test_invalid_jwt_rejected(self):
        """유효하지 않은 JWT는 거부되어야 함"""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
    
    async def test_expired_jwt_rejected(self):
        """만료된 JWT는 거부되어야 함"""
        expired_token = create_expired_token()
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
    
    async def test_rate_limiting_enforced(self):
        """Rate Limiting이 적용되어야 함"""
        for _ in range(6):
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "wrong"}
            )
        
        assert response.status_code == 429  # Too Many Requests

class TestAuthorization:
    """권한 보안 테스트"""
    
    async def test_user_cannot_access_other_user_data(self):
        """다른 사용자의 데이터에 접근할 수 없어야 함"""
        token_user_a = await get_token_for_user("user_a")
        
        response = await client.get(
            "/api/v1/users/user_b",
            headers={"Authorization": f"Bearer {token_user_a}"}
        )
        
        assert response.status_code == 403

class TestInputValidation:
    """입력 검증 테스트"""
    
    async def test_sql_injection_prevented(self):
        """SQL Injection이 차단되어야 함"""
        malicious_input = "'; DROP TABLE users; --"
        
        response = await client.get(
            f"/api/v1/facilities/search?name={malicious_input}"
        )
        
        # 에러가 아닌 빈 결과 반환
        assert response.status_code == 200
        assert len(response.json()) == 0
    
    async def test_xss_prevented(self):
        """XSS가 차단되어야 함"""
        xss_payload = "<script>alert('XSS')</script>"
        
        response = await client.post(
            "/api/v1/reviews",
            json={"content": xss_payload},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 스크립트가 sanitize되어야 함
        review = response.json()
        assert "<script>" not in review["content"]

class TestDataEncryption:
    """데이터 암호화 테스트"""
    
    async def test_phone_number_encrypted_in_database(self):
        """전화번호가 DB에 암호화되어 저장되어야 함"""
        # 사용자 등록
        await client.post("/api/v1/users", json={
            "email": "test@example.com",
            "phone": "010-1234-5678"
        })
        
        # DB에서 직접 조회
        user = await db.fetch_one(
            "SELECT phone_encrypted FROM users WHERE email = 'test@example.com'"
        )
        
        # 평문이 아니어야 함
        assert user["phone_encrypted"] != "010-1234-5678"
        assert len(user["phone_encrypted"]) > 20  # 암호화된 길이
```

### 6.2 정기 보안 감사

**주간 보안 체크리스트**:
```markdown
- [ ] 실패한 로그인 시도 검토
- [ ] API Rate Limit 초과 사례 검토
- [ ] 의심스러운 IP 주소 확인
- [ ] 데이터베이스 접근 로그 검토
- [ ] 파일 업로드 실패 사례 검토
```

**월간 보안 체크리스트**:
```markdown
- [ ] 의존성 취약점 스캔 (npm audit, pip-audit)
- [ ] OWASP ZAP 스캔 실행
- [ ] 접근 제어 정책 검토
- [ ] 사용자 권한 감사
- [ ] 시크릿 로테이션 확인
- [ ] 백업 및 복구 테스트
```

**분기별 보안 체크리스트**:
```markdown
- [ ] 침투 테스트 수행
- [ ] 보안 정책 문서 업데이트
- [ ] 직원 보안 교육
- [ ] 인시던트 대응 훈련
- [ ] 규정 준수 감사 (GDPR, 개인정보보호법)
```

---

이 문서는 서울케어플러스의 보안 취약점을 식별하고, 개선 방안을 제시합니다. 다음 문서에서는 데이터 파이프라인 개선 및 세분화가 필요한 기능들을 다루겠습니다.
