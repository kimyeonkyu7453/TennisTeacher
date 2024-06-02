document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.getElementById('uploadButton');
    const preview = document.getElementById('preview');
    const uploadProgressBar = document.getElementById('uploadProgressBar');
    const uploadProgressText = document.getElementById('uploadProgressText');
    const videoSelect = document.getElementById('videoSelect');
    const analyzeButton = document.getElementById('analyzeButton');
    const analysisProgressBar = document.getElementById('analysisProgressBar');
    const analysisProgressText = document.getElementById('analysisProgressText');
    const checkResultButton = document.getElementById('checkResultButton');
    const resultImage = document.getElementById('resultImage');
    const backButton = document.getElementById('backButton');
    let selectedVideoPath = '';

    backButton.addEventListener('click', function() {
        window.history.back();
    });

    // 파일 선택 시 미리보기
    fileInput.addEventListener('change', function() {
        const file = fileInput.files[0];
        if (file) {
            const url = URL.createObjectURL(file);
            preview.src = url;
            preview.style.display = 'block';
        } else {
            preview.style.display = 'none';
        }
    });

    // 파일 업로드 처리
    uploadButton.addEventListener('click', function() {
        const file = fileInput.files[0];
        if (!file) {
            alert('업로드할 파일을 선택하세요.');
            return;
        }

        const formData = new FormData();
        formData.append('video', file);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload', true);

        xhr.upload.onprogress = function(event) {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                uploadProgressBar.value = percentComplete;
                uploadProgressText.textContent = `진행률: ${percentComplete.toFixed(2)}%`;
            }
        };

        xhr.onload = function() {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                alert('업로드가 완료되었습니다.');
                selectedVideoPath = response.filePath;  // 업로드된 파일 경로 저장
                loadVideoOptions();
            } else {
                alert('업로드 중 오류가 발생했습니다.');
            }
        };

        xhr.onerror = function() {
            alert('업로드 중 오류가 발생했습니다.');
        };

        uploadProgressBar.style.display = 'block';
        uploadProgressText.style.display = 'block';
        uploadProgressBar.value = 0;
        uploadProgressText.textContent = '진행률: 0%';

        xhr.send(formData);
    });

    // 비디오 목록 로드
    function loadVideoOptions() {
        fetch('/videos')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok ' + response.statusText);
                }
                return response.json();
            })
            .then(videos => {
                videoSelect.innerHTML = '<option value="">영상 선택</option>';
                videos.forEach(video => {
                    const option = document.createElement('option');
                    option.value = video.path;
                    option.textContent = video.name;
                    videoSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error fetching video list:', error);
                alert('비디오 목록을 불러오는 중 오류가 발생했습니다: ' + error.message);
            });
    }

    // 비디오 선택 시 미리보기 제거
    videoSelect.addEventListener('change', function() {
        selectedVideoPath = videoSelect.value;
    });

    // 분석하기 버튼 클릭 시
    analyzeButton.addEventListener('click', function() {
        if (!selectedVideoPath) {
            alert('먼저 영상을 선택하세요.');
            return;
        }

        analysisProgressBar.style.display = 'block';
        analysisProgressText.style.display = 'block';
        analysisProgressBar.value = 0;
        analysisProgressText.textContent = '진행률: 0%';

        const interval = setInterval(() => {
            fetch('/get-analysis-progress')
                .then(response => response.json())
                .then(data => {
                    const progress = data.progress;
                    const currentProgress = analysisProgressBar.value;
                    const increment = (progress - currentProgress) / 10; // 자연스럽게 증가시키기 위한 계산
                    let counter = 0;

                    const smoothIncrement = setInterval(() => {
                        if (counter >= 10) {
                            clearInterval(smoothIncrement);
                        } else {
                            analysisProgressBar.value += increment;
                            analysisProgressText.textContent = `진행률: ${analysisProgressBar.value.toFixed(2)}%`;
                            counter++;
                        }
                    }, 100);

                    if (progress >= 100) {
                        clearInterval(interval);
                    }
                })
                .catch(error => {
                    console.error('Error fetching analysis progress:', error);
                });
        }, 1000);

        fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filePath: selectedVideoPath })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            alert(data.message);  // 팝업이 뜨도록 합니다.
            checkResultButton.style.display = 'block';  // 팝업 이후에 버튼을 표시합니다.
            analysisProgressBar.value = 100;
            analysisProgressText.textContent = '진행률: 100%';
        })
        .catch(error => {
            console.error('Error analyzing video:', error);
            alert('비디오 분석 중 오류가 발생했습니다: ' + error.message);
        });
    });

    // 분석결과 확인하기 버튼 클릭 시
    checkResultButton.addEventListener('click', function() {
        window.location.href = '/result.html';
    });

    // 페이지 로드 시 비디오 옵션 로드
    loadVideoOptions();

    document.getElementById('checkResultButton').addEventListener('click', function() {
        window.location.href = '/result.html';
    });
});
