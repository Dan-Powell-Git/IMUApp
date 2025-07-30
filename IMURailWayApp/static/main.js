let recordCount = 0;
let recordInterval= null;

document.addEventListener("DOMContentLoaded", function(){
    const startButton = document.getElementById('start_button');
    const stop_button = document.getElementById('stop_button');
    const statusMsg = document.getElementById('statusMsg');
    const restartButton = document.getElementById('restart_button');
    const recordCounter = document.getElementById('recordCounter');
    const cancelButton = document.getElementById('cancelButton');

    let recording = false;
    let pollinterval = null; 
    
    async function startRecordingProcess(){
        const res = await fetch('/start_recording', {method:'POST'})
        // why no check to make sure status of 200?
        recording = true;
        statusMsg.textContent = 'Recording Started'
        startButton.style.display = 'none'
        stop_button.style.display = 'inline-block'
        restartButton.style.display = 'inline-block'
        cancelButton.style.display = 'inline-block'

        if (restartButton){restartButton.style.display = 'inline-block';}
        recordCounter.style.display = 'inline-block'

        pollinterval = setInterval( async() =>{
            const recRes = await fetch('/record_count');
            const recJson = await resRes.json();
            recordCounter.textContent = `Records Received: ${json.count}`
        }, 30000)
    }
    async function stopRecordingProcess() {
        const res = await fetch('/stop_recording', {method: 'POST'});
        const json = await res.json();
        const status = json.status;

        if (res.status === 200){
            statusMsg.textContent = 'Recording Stopped'
            startButton.style.display = 'inline-block'
            stop_button.style.display = 'none'
            if(restartButton) restartButton.style.display = 'none'
            recordCounter.style.display = 'none'
            recording = false

            if (pollinterval){
                clearInterval(pollinterval)
                pollinterval = null
            }
            return true
        }
        else {
            statusMsg.textContent = `Failed to stop recording due to ${json.message}`
            return false;
        }

    }
    async function cancelRecordingProcess(){
        if (confirm('Are you sure you want to cancel the recording process')){
            
        }
    }

    if (startButton){
        startButton.addEventListener('click', startRecordingProcess)
    }
    if (stop_button){
        stop_button.addEventListener('click', stopRecordingProcess)
    }
    if (restartButton){
        restartButton.addEventListener('click', async() => {
            statusMsg.textContent = 'Attempting to restart recording...'
            const stoppedSuccessfully = await stopRecordingProcess();

            if (stoppedSuccessfully|| !recording){
                await new Promise(resolve => setTimeout(resolve,1000))
                await startRecordingProcess();

                statusMsg.textContent = "Recording Restarted"
            }
            else{
                statusMsg.textContent =  "Failed to restart recording"
            }
        })
    }

})