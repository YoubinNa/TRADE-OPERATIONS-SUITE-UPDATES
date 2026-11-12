'use strict';
// Public operational hold, read with GitHub's built-in token or anonymously. No private credential.
function reader(jobId,token,fetchImpl=fetch){
  if(!/^[a-zA-Z0-9._-]{1,120}$/.test(jobId))throw Error('INVALID_JOB_ID');
  return async()=>{
    let r;
    try{r=await fetchImpl('https://api.github.com/repos/YoubinNa/TRADE-OPERATIONS-SUITE-UPDATES/contents/publisher/control/jobs/'+jobId+'.json?ref=main',{
      redirect:'error',signal:AbortSignal.timeout(15000),
      headers:{Accept:'application/vnd.github+json',...(token?{Authorization:'Bearer '+token}:{}),'Cache-Control':'no-cache'}
    });}catch{throw Error('SHARED_CONTROL_UNAVAILABLE');}
    if(!r.ok)throw Error('SHARED_CONTROL_UNAVAILABLE');
    const data=await r.json();
    if(data.encoding!=='base64')throw Error('SHARED_CONTROL_ENCODING');
    const control=JSON.parse(Buffer.from(data.content.replace(/\s/g,''),'base64').toString('utf8'));
    if(control.schema!==1)throw Error('SHARED_CONTROL_SCHEMA');
    return control;
  };
}
module.exports={reader};
