'use strict';
// Public execution metadata only. Reuses the existing live hold and stage authorizer.
const fs=require('node:fs'),crypto=require('node:crypto'),cp=require('node:child_process');
const {authorize}=require('./execution-control-guard.cjs');
const {reader}=require('./shared-control.cjs');
const stages={prepare:['public-stage','preflight'],stage:['public-stage'],preflight:['preflight'],activate:['activate'],full:['public-stage','preflight','activate'],inspect:[]};
const candidatePattern=/^publisher\/candidates\/v0\.\d+\.\d+\.json$/;
const idPattern=/^[a-zA-Z0-9][a-zA-Z0-9._-]{0,119}$/;
const requestPattern=/^publisher\/execution-requests\/([a-zA-Z0-9][a-zA-Z0-9._-]{0,119})\.json$/;
const sha=s=>crypto.createHash('sha256').update(s).digest('hex');
function fail(code){throw Error(code);}
function validate(values){
 if(!candidatePattern.test(values.candidate||'')||!idPattern.test(values.job_id||'')||!Object.hasOwn(stages,values.operation))fail('INVALID_EXECUTION_SCOPE');
 return values;
}
function parseRequest(path,raw){
 if(raw.length>4096)fail('REQUEST_TOO_LARGE');
 const match=path.match(requestPattern);if(!match)fail('INVALID_REQUEST_PATH');
 let r;try{r=JSON.parse(raw);}catch{fail('INVALID_REQUEST_JSON');}
 const keys=['schema','request_id','candidate','candidate_sha256','operation','job_id'];
 if(!r||Array.isArray(r)||Object.keys(r).length!==keys.length||keys.some(k=>!Object.hasOwn(r,k))||r.schema!==1||
    r.request_id!==match[1]||!idPattern.test(r.request_id)||!/^[a-f0-9]{64}$/.test(r.candidate_sha256||''))fail('INVALID_REQUEST_SCHEMA');
 return validate(r);
}
function selectAdded(changes){
 const rows=changes.trim().split('\n').filter(Boolean).map(row=>row.split('\t'));
 if(rows.length!==1||rows[0].length!==2||rows[0][0]!=='A'||!requestPattern.test(rows[0][1]))fail('ONE_NEW_IMMUTABLE_REQUEST_REQUIRED');
 return rows[0][1];
}
async function resolve({eventName,event,sha:commit,manual,changed,readFile,readControl}){
 let r;
 if(eventName==='push'){
  if(event.ref!=='refs/heads/main'||event.deleted||event.forced||!/^[a-f0-9]{40}$/.test(event.before||'')||
     /^0+$/.test(event.before)||event.after!==commit||!/^[a-f0-9]{40}$/.test(commit||''))fail('INVALID_PUSH_EVENT');
  const path=selectAdded(await changed(event.before,commit));
  r=parseRequest(path,await readFile(path));
 }else if(eventName==='workflow_dispatch'){
  r=validate({candidate:manual.candidate,operation:manual.operation||'prepare',job_id:manual.job_id});
 }else fail('UNSUPPORTED_EXECUTION_EVENT');
 const raw=await readFile(r.candidate),digest=sha(raw);
 if(r.candidate_sha256&&r.candidate_sha256!==digest)fail('REQUEST_CANDIDATE_HASH_MISMATCH');
 const control=await readControl(r.job_id);
 if(control?.schema!==1||typeof control.paused!=='boolean')fail('INVALID_SHARED_CONTROL');
 if(r.operation==='inspect'){
  const permitted=[];
  for(const stage of ['public-stage','preflight','activate']){
   try{await authorize(raw,stage,control);permitted.push(stage);}catch(e){
    if(!['DEPLOYMENT_PAUSED','STAGE_NOT_AUTHORIZED'].includes(e.message))throw e;
   }
  }
  return {...r,candidate_sha256:digest,readOnly:true,paused:control.paused,permittedStages:permitted};
 }
 // Verify the full requested scope before starting; each existing stage re-reads the hold.
 for(const stage of stages[r.operation])await authorize(raw,stage,control);
 return {...r,candidate_sha256:digest,readOnly:false,paused:false};
}
if(require.main===module)(async()=>{
 const event=JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH,'utf8'));
 const result=await resolve({eventName:process.env.GITHUB_EVENT_NAME,event,sha:process.env.GITHUB_SHA,
  manual:{candidate:process.env.INPUT_CANDIDATE,operation:process.env.INPUT_OPERATION,job_id:process.env.INPUT_JOB_ID},
  changed:(before,after)=>cp.execFileSync('git',['diff','--no-renames','--name-status',before,after,'--','publisher/execution-requests/'],{encoding:'utf8'}),
  readFile:path=>fs.readFileSync(path),
  readControl:id=>reader(id,process.env.RELEASE_CONTROL_TOKEN)()});
 const out=['candidate='+result.candidate,'operation='+result.operation,'job_id='+result.job_id].join('\n')+'\n';
 fs.appendFileSync(process.env.GITHUB_OUTPUT,out);
 const summary={operation:result.operation,requestId:result.request_id||null,candidate:result.candidate,candidateSha256:result.candidate_sha256,
  readOnly:result.readOnly,paused:result.paused,permittedStages:result.permittedStages,executionResolved:true};
 console.log(JSON.stringify(summary));
 if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,'Execution scope: '+JSON.stringify(summary)+'\n');
})().catch(e=>{console.error(/^[A-Z_]{1,80}$/.test(e.message)?e.message:'EXECUTION_REQUEST_BLOCKED');process.exitCode=1;});
module.exports={parseRequest,selectAdded,resolve,stages};
