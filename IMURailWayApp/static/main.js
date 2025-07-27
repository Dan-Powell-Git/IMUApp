let recordCount = 0;
let recordInterval= null;

document.addEventListener("DOMContentLoaded", function(){
    const startButton = document.getElementById('start_button');
    const stop_button = document.getElementById('stop_button');
    const statusMsg = document.getElementById('statusMsg');
    const recordCounter = document.getElementById('recordCounter');

    let trystopRecording = true;

    let pollinterval = null; 
    
    if (startButton){
        startButton.addEventListener('click', async() => {
            const res = await fetch('/start_recording', {method: 'POST'});

            statusMsg.textContent = 'Recording Started';
            startButton.style.display = "none";
            stop_button.style.display = "inline-block";
            countNum = (await fetch("/record_count")).json()
            recordCounter.style.display = "inline-block";


            //counter
            pollinterval = setInterval( async() =>{
                const res = await fetch("/record_count")
                const json = await res.json();
                recordCounter.textContent = `Records received: ${json.count}`;
            }, 30000)
        });
    }
    if (stop_button){
        stop_button.addEventListener('click', async() => {
        while (trystopRecording){
            const res = await fetch('/stop_recording', {method: 'POST'});
            const json = await res.json()
            const status = await json.status
            console.log('response', json)
            console.log('response message:\n', status)
            //console.log('response json:\n', res.json())
            

            if (res.status == 200){
                statusMsg.textContent = "Recording stopped.";
                stop_button.style.display = "none";
                startButton.style.display = "inline-block";
            }
            else{
                if (confirm('Error encountered when stopping Recording: \n' + json.message + "\nClick Cancel to abandon recording. Click Yes to attempt to reflush.")){
                    

                }
                stop_button.style.display = "inline-block";
                startButton.style.display = "none";
            }

            clearInterval(recordInterval);}
        })
    }
})