const express = require('express');
const path = require('path');
const multer = require('multer');
const fs = require('fs');
const cors = require('cors');
const { exec } = require('child_process');
const app = express();

// 환경 변수 설정
const port = process.env.PORT || 8080;
const uploadsDir = process.env.UPLOADS_DIR || '/app/uploads';
const openposeDir = process.env.OPENPOSE_DIR || '/app/openpose';

let analysisResult = {}; // 분석 결과를 저장할 객체 초기화

// 업로드 스토리지 설정
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadsDir);
    },
    filename: (req, file, cb) => {
        cb(null, Date.now() + path.extname(file.originalname));
    }
});

const upload = multer({ storage: storage });

app.use(cors());
app.use(express.json());
app.use(express.static(uploadsDir));
app.use(express.static('/app/public'));

// 업로드 처리
app.post('/upload', upload.single('video'), (req, res) => {
    if (!req.file) {
        console.error('No file uploaded');
        return res.status(400).send('No file uploaded.');
    }
    console.log('File uploaded:', req.file.filename);

    // 파일 권한 설정
    fs.chmodSync(req.file.path, 0o777);  // 모든 사용자에게 읽기/쓰기 권한 부여

    res.json({ filePath: `${uploadsDir}/${req.file.filename}`, fileName: req.file.originalname });
});

// 비디오 목록 가져오기
app.get('/videos', (req, res) => {
    console.log('GET /videos 요청 수신');
    fs.readdir(uploadsDir, (err, files) => {
        if (err) {
            console.error('파일 목록을 불러오는 중 오류 발생:', err);
            return res.status(500).json({ error: '파일 목록을 불러오는 중 오류가 발생했습니다.' });
        }
        const videos = files.map(file => ({
            name: file,
            path: `${uploadsDir}/${file}`
        }));
        res.json(videos);
    });
});

// 비디오 분석
app.post('/analyze', (req, res) => {
    console.log('POST /analyze 요청 수신:', req.body.filePath);
    const filePath = path.join(uploadsDir, path.basename(req.body.filePath));
    console.log(`Analyzing file: ${filePath}`);

    analysisResult = {};

    const analyzeScript = path.join(openposeDir, 'analyze_video.py');
    exec(`python3 ${analyzeScript} ${filePath}`, (error, stdout, stderr) => {
        if (error) {
            console.error(`exec error: ${error}`);
            return res.status(500).json({ error: '분석 중 오류 발생', details: error.message });
        }
        console.log(`stdout: ${stdout}`);
        console.log(`stderr: ${stderr}`);

        const resultPath = path.join(openposeDir, 'result.json');
        fs.readFile(resultPath, 'utf8', (err, data) => {
            if (err) {
                console.error(`Error reading result file: ${err}`);
                return res.status(500).json({ error: '결과 파일 읽기 오류', details: err.message });
            }
            analysisResult = JSON.parse(data);
            res.json({ message: '분석 완료', result: analysisResult });
        });
    });
});

// 분석 결과 가져오기
app.get('/get-analysis-result', (req, res) => {
    res.json(analysisResult);
});

// 서버 시작
app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
