'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {resolve,parseRequest,selectAdded}=require('./resolve-execution.cjs');
const raw=Buffer.from('{"synthetic":true}\n'),digest=crypto.createHash('sha256').update(raw).digest('hex');
function fixture(operation='prepare'){
 const request={schema:1,request_id:'synthetic-one',candidate:'publisher/candidates/v0.9.999.json',candidate_sha256:digest,operation,job_id:'synthetic-job'};
 const control={schema:1,paused:false,releaseAuthorization:{candidateFileSha256:digest,reference:'synthetic approval',allowedStages:['public-stage','preflight']}};
 const io={eventName:'push',event:{ref:'refs/heads/main',before:'a'.repeat(40),after:'b'.repeat(40),forced:false,deleted:false},sha:'b'.repeat(40),
  changed:()=> 'A\tpublisher/execution-requests/synthetic-one.json\n',
  readFile:p=>p.startsWith('publisher/candidates/')?raw:Buffer.from(JSON.stringify(request)),
  readControl:async id=>{assert.equal(id,'synthetic-job');return control;}};
 return {request,control,io};
}
test('connector push resolves a new immutable request and exact candidate',async()=>{
 const f=fixture(),r=await resolve(f.io);assert.equal(r.operation,'prepare');assert.equal(r.candidate_sha256,digest);assert.equal(r.readOnly,false);
});
test('inspect reports a real hold without enabling any execution stage',async()=>{
 const f=fixture('inspect');f.control.paused=true;
 const r=await resolve(f.io);assert.equal(r.operation,'inspect');assert.equal(r.readOnly,true);assert.equal(r.paused,true);assert.deepEqual(r.permittedStages,[]);
});
test('prepare authorization cannot start full or activate',async()=>{
 for(const op of ['activate','full'])await assert.rejects(resolve(fixture(op).io),/STAGE_NOT_AUTHORIZED/);
});
test('exact full approval resolves without overriding per-stage live checks',async()=>{
 const f=fixture('full');f.control.releaseAuthorization.allowedStages.push('activate');
 assert.equal((await resolve(f.io)).operation,'full');
 f.control.paused=true;await assert.rejects(resolve(f.io),/DEPLOYMENT_PAUSED/);
});
test('request hash and control hash are independently enforced',async()=>{
 let f=fixture();f.request.candidate_sha256='0'.repeat(64);await assert.rejects(resolve(f.io),/REQUEST_CANDIDATE_HASH_MISMATCH/);
 f=fixture();f.control.releaseAuthorization.candidateFileSha256='0'.repeat(64);await assert.rejects(resolve(f.io),/STAGE_NOT_AUTHORIZED/);
});
test('missing, malformed and unavailable control fail closed',async()=>{
 for(const c of [null,{}, {schema:1,paused:'false'}]){const f=fixture();f.io.readControl=async()=>c;await assert.rejects(resolve(f.io),/INVALID_SHARED_CONTROL/);}
 const f=fixture();f.io.readControl=async()=>{throw Error('SHARED_CONTROL_UNAVAILABLE');};await assert.rejects(resolve(f.io),/SHARED_CONTROL_UNAVAILABLE/);
});
test('modified, deleted, renamed and multiple request files cannot trigger execution',()=>{
 for(const change of ['M\tpublisher/execution-requests/a.json','D\tpublisher/execution-requests/a.json','R100\told\tpublisher/execution-requests/a.json','A\tpublisher/execution-requests/a.json\nA\tpublisher/execution-requests/b.json',''])assert.throws(()=>selectAdded(change),/ONE_NEW/);
});
test('non-main, deleted, forced and mismatched push events are rejected',async()=>{
 for(const patch of [{ref:'refs/heads/review'},{deleted:true},{forced:true},{before:'0'.repeat(40)},{after:'c'.repeat(40)}]){
  const f=fixture();Object.assign(f.io.event,patch);await assert.rejects(resolve(f.io),/INVALID_PUSH_EVENT/);
 }
});
test('schema, size, traversal, newline injection and filename mismatch are rejected',()=>{
 for(const patch of [{schema:2},{request_id:'different'},{extra:'not allowed'},{candidate:'../secret'},{job_id:'job\noperation=full'},{operation:'publish'},{candidate_sha256:'bad'}]){
  const f=fixture();Object.assign(f.request,patch);assert.throws(()=>parseRequest('publisher/execution-requests/synthetic-one.json',Buffer.from(JSON.stringify(f.request))));
 }
 assert.throws(()=>parseRequest('publisher/execution-requests/synthetic-one.json',Buffer.alloc(4097)),/REQUEST_TOO_LARGE/);
 assert.throws(()=>parseRequest('publisher/execution-requests/synthetic-one.json',Buffer.from('{')),/INVALID_REQUEST_JSON/);
});
test('manual dispatch keeps default prepare and cannot bypass holds',async()=>{
 const f=fixture();f.io.eventName='workflow_dispatch';f.io.manual={candidate:f.request.candidate,job_id:f.request.job_id};
 assert.equal((await resolve(f.io)).operation,'prepare');
 f.control.paused=true;await assert.rejects(resolve(f.io),/DEPLOYMENT_PAUSED/);
});
test('unsupported event cannot execute',async()=>{
 const f=fixture();f.io.eventName='pull_request';await assert.rejects(resolve(f.io),/UNSUPPORTED_EXECUTION_EVENT/);
});
