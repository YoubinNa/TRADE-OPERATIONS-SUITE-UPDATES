'use strict';
const fs=require('node:fs'),crypto=require('node:crypto');
const {reader}=require('./shared-control.cjs');
async function authorize(raw,stage,control){
  if(control?.schema!==1||control.paused!==false)throw Error('DEPLOYMENT_PAUSED');
  const a=control.releaseAuthorization,digest=crypto.createHash('sha256').update(raw).digest('hex');
  if(!a||a.candidateFileSha256!==digest||!a.reference||!Array.isArray(a.allowedStages)||!a.allowedStages.includes(stage))
    throw Error('STAGE_NOT_AUTHORIZED');
  return true;
}
if(require.main===module)(async()=>{
  const [spec,stage]=process.argv.slice(2);
  if(!/^publisher\/candidates\/v0\.\d+\.\d+\.json$/.test(spec)||!['public-stage','preflight','activate','publish'].includes(stage))throw Error('CONTROL_SCOPE');
  const control=await reader(process.env.RELEASE_CONTROL_JOB_ID,process.env.RELEASE_CONTROL_TOKEN)();
  await authorize(fs.readFileSync(spec),stage,control);
})().catch(()=>{console.error('EXECUTION_CONTROL_BLOCKED');process.exitCode=1;});
module.exports={authorize};
