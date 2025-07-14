let recordCount = 0;
let recordInterval= null;

document.addEventListener("DOMContentLoaded", function(){
    const startButton = document.getElementById('start_button');
    const stop_button = document.getElementById('stop_button');
    const statusMsg = document.getElementById('statusMsg');
    const recordCounter = document.getElementById('recordCounter');

    let pollinterval = null; 
    
    if (startButton){
        startButton.addEventListener('click', async() => {
            const res = await fetch('/start_recording', {method: 'POST'});

            statusMsg.textContent = 'Recording Started';
            startButton.style.display = "none";
            stop_button.style.display = "inline-block";

            //counter
            pollinterval = setInterval( async() =>{
                const res = await fetch("/record_count")
                const json = await res.json();

                recordCounter.textContent = `Records received: ${json.count}`;
            }, 1000)
        });
    }
    if (stop_button){
        stop_button.addEventListener('click', async() => {
            const res = await fetch('/stop_recording', {method: 'POST'});

            statusMsg.textContent = "Recording stopped.";
            stopBtn.style.display = "none";
            startBtn.style.display = "inline-block";

            clearInterval(recordInterval);
        })
    }
})