document.getElementById('checkResultsButton').addEventListener('click', function() {
    fetch('/result.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            let resultsTable = document.getElementById('resultsTable');
            resultsTable.innerHTML = ''; // 기존 내용을 지움
            data.forEach(result => {
                let row = resultsTable.insertRow();
                let cellFrom = row.insertCell(0);
                let cellTo = row.insertCell(1);
                let cellAngle = row.insertCell(2);
                let cellIsCorrect = row.insertCell(3);

                cellFrom.innerHTML = result.From;
                cellTo.innerHTML = result.To;
                cellAngle.innerHTML = result.Angle.toFixed(2);
                cellIsCorrect.innerHTML = result.IsCorrect ? 'Correct' : 'Incorrect';
            });
        })
        .catch(error => {
            console.error('Error fetching the result:', error);
            alert('분석 결과를 불러오는 중 오류가 발생했습니다.');
        });
});
