const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.resolve(__dirname, '../../../static/js/bookkeeper_verification_ui.js'), 'utf8');
const makeNode = () => ({value:'',textContent:'',hidden:false,disabled:false,handlers:{},addEventListener(type, fn){this.handlers[type]=fn;},focus(){this.focused=true;}});
const ids=['verificationProofForm','verificationDocumentType','verificationOtherDocument','verificationDocumentName','verificationProofFile','verificationClearSelection','verificationSubmitProof','verificationSubmissionNotice','verificationProofStatus','verificationSavedDocument','verificationSavedProof'];
function setup(saved=null, response={ok:true,status:200,json:async()=>({ok:true,proof:{revision:'saved-revision',download_url:'/api/verification/proof/saved-revision/'}})}) {
 const nodes=Object.fromEntries(ids.map(id=>[id,makeNode()]));
 const form=nodes.verificationProofForm;
 form.getAttribute=()=>'/api/verification/proof/'; form.reportValidity=()=>true;
 nodes.verificationSavedProof.textContent=JSON.stringify(saved);
 const file=nodes.verificationProofFile; file.files=[];
 Object.defineProperty(file,'value',{get(){return this.fileValue||'';},set(v){this.fileValue=v;if(!v)this.files=[];}});
 const calls=[];
 class Data extends Map {constructor(){super();this.set('document',file.files[0]);}}
 vm.runInNewContext(source,{document:{getElementById:id=>nodes[id]}, FormData:Data,
   fetch:async(url,options)=>{calls.push({url,options});if(response instanceof Error)throw response;return response;},
   localStorage:{setItem(){throw new Error('Must not persist private selections in browser storage');}}});
 const select=()=>{nodes.verificationDocumentType.value='business_permit'; file.files=[{name:'proof.png',size:100}];file.handlers.change();};
 return {nodes,calls,select,submit:()=>form.handlers.submit({preventDefault(){}})};
}
(async()=>{
 let test=setup(); const n=test.nodes;
 assert(n.verificationSubmitProof.disabled); assert(n.verificationOtherDocument.hidden);
 n.verificationDocumentType.value='other';n.verificationDocumentType.handlers.change();assert(!n.verificationOtherDocument.hidden);assert(n.verificationDocumentName.required);
 n.verificationDocumentName.value='Experience letter';n.verificationProofFile.files=[{size:100}];n.verificationDocumentName.handlers.input();assert(!n.verificationSubmitProof.disabled);
 n.verificationClearSelection.handlers.click();assert(n.verificationDocumentType.focused);assert(n.verificationSubmitProof.disabled);assert.equal(n.verificationProofFile.files.length,0);
 test.select(); await test.submit();assert.equal(test.calls.length,1);assert.equal(test.calls[0].options.body.get('revision'),'');assert.equal(n.verificationProofStatus.textContent,'Submitted');assert.equal(n.verificationProofFile.files.length,0);
 test=setup({revision:'old'});test.select();await test.submit();assert.equal(test.calls[0].options.body.get('revision'),'old');
 for(const response of [new Error('offline'),{ok:false,status:503,json:async()=>({ok:false,message:'Reload to check'})},{ok:true,status:200,json:async()=>({ok:true})}]){
  test=setup(null,response);test.select();await test.submit();assert.equal(test.calls.length,1);assert.equal(test.nodes.verificationProofFile.files.length,1);assert(test.nodes.verificationSubmitProof.disabled);await test.submit();assert.equal(test.calls.length,1,'Unknown writes must not retry');
 }
 test=setup(null,{ok:false,status:400,json:async()=>({ok:false,message:'Choose a readable file'})});test.select();await test.submit();assert(!test.nodes.verificationSubmitProof.disabled);assert.equal(test.nodes.verificationProofFile.files.length,1);
 test=setup();test.select();test.nodes.verificationProofFile.files[0].size=6*1024*1024;await test.submit();assert.equal(test.calls.length,0);
 vm.runInNewContext(source,{document:{getElementById:()=>null}});
 console.log('Proof submission checks passed: choices, clear, saved revision, confirmed success, rejected/unknown writes, draft preservation, size limit.');
})().catch(e=>{console.error(e);process.exitCode=1;});
