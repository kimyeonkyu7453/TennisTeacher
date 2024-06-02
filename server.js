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
let analysisProgress = 0; // 분석 진행률 초기화

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

    // 해상도 낮추기 스크립트 실행
    const inputFilePath = path.join(uploadsDir, req.file.filename);
    const outputFilePath = path.join(uploadsDir, 'resized_' + req.file.filename);
    exec(`python3 resize_video.py "${inputFilePath}" "${outputFilePath}"`, (error, stdout, stderr) => {
        if (error) {
            console.error(`Error resizing video: ${error.message}`);
            return res.status(500).send('Error resizing video.');
        }
        console.log('Video resized:', outputFilePath);
        res.json({ filePath: outputFilePath, fileName: req.file.originalname });
    });
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

// 분석 진행률 가져오기
app.get('/get-analysis-progress', (req, res) => {
    res.json({ progress: analysisProgress });
});

// 비디오 분석
app.post('/analyze', (req, res) => {
    console.log('POST /analyze 요청 수신:', req.body.filePath);
    const filePath = path.join(uploadsDir, path.basename(req.body.filePath));
    console.log(`Analyzing file: ${filePath}`);

    analysisResult = {};
    analysisProgress = 0; // 분석 진행률 초기화

    const analyzeScript = path.join(openposeDir, 'analyze_video.py');
    const analyzeProcess = exec(`python3 ${analyzeScript} ${filePath}`);

    // 진행률을 주기적으로 업데이트하는 함수
    const updateProgress = setInterval(() => {
        analysisProgress += 10;
        if (analysisProgress >= 100) {
            clearInterval(updateProgress);
        }
    }, 1000);

    analyzeProcess.stdout.on('data', (data) => {
        console.log(`stdout: ${data}`);
        // 데이터에서 진행률을 추출하여 업데이트 (예: "Progress: 50%")
        const progressMatch = data.match(/Progress: (\d+)%/);
        if (progressMatch) {
            analysisProgress = parseInt(progressMatch[1]);
        }
    });

    analyzeProcess.stderr.on('data', (data) => {
        console.error(`stderr: ${data}`);
    });

    analyzeProcess.on('close', (code) => {
        clearInterval(updateProgress);
        if (code !== 0) {
            console.error(`analyze process exited with code ${code}`);
            return res.status(500).json({ error: '분석 중 오류 발생' });
        }

        const resultPath = path.join(openposeDir, 'result.json');
        fs.readFile(resultPath, 'utf8', (err, data) => {
            if (err) {
                console.error(`Error reading result file: ${err}`);
                return res.status(500).json({ error: '결과 파일 읽기 오류', details: err.message });
            }
            analysisResult = JSON.parse(data);
            res.json({ message: '분석 완료', result: analysisResult });
            analysisProgress = 100; // 분석 완료 시 진행률 100%로 설정
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
