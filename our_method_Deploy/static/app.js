const $ = id => document.getElementById(id);
const basePath = location.pathname.startsWith('/plc-generation') ? '/plc-generation' : '';
let catalog, currentJob, pollHandle, approvalTimer, approvalJobId, engineeringJobId=null, approvalSubmitting=false,submissionBusy=false,validationStatusBusy=false,modelStatusBusy=false,requirementCheckBusy=false,validationOverall=null,ladderBlobUrl=null,pollFailureCount=0,taskFilter='all',taskCenterBusy=false,historyPage=1;
let modelStatusById=new Map();
let trackedJobs=new Map();
let lastTaskCapacity={slots:4,running:0,queued:0};
let historyPagination={page:1,page_size:12,total:0,pages:1};
const jobRecovery=window.PlcJobRecovery;
const APPROVAL_DELAY_MS=5000;
const TRACKED_JOBS_KEY='plc_tracked_jobs_v1';
const VENDOR_PROCESS_STEPS=[
  {id:'input_check',label:'任务入队'},
  {id:'project_load',label:'装载工程'},
  {id:'communication_setup',label:'绑定通信'},
  {id:'program_import',label:'导入程序'},
  {id:'ispsoft_compile',label:'ISPSoft 编译'},
  {id:'controller_download',label:'下载程序'},
  {id:'commgr_runtime',label:'COMMGR 仿真'},
  {id:'oracle_evaluation',label:'Oracle 判定'},
  {id:'deployment_compile',label:'交付工程编译'},
  {id:'project_package',label:'工程封装'}
];
const VENDOR_PHASE_RANK={queued:0,input_check:0,project_load:1,communication_setup:2,program_import:3,ispsoft_compile:4,controller_download:5,commgr_runtime:6,oracle_evaluation:7,deployment_compile:8,project_package:9,result_publish:9,complete:10};
const STATUS_LABELS={
  contract_queued:'契约排队中',contract_generating:'正在生成契约',awaiting_contract_approval:'等待确认',
  generation_queued:'生成任务排队中',generating:'生成与验证中',verified_success:'验证通过',
  cancelling:'正在取消',cancelled:'已取消',generation_failed:'生成未通过',contract_failed:'契约生成失败',infrastructure_error:'基础设施错误'
};
const statusLabel=value=>STATUS_LABELS[value]||value||'未知状态';
const ACTIVE_JOB_STATUSES=['contract_queued','contract_generating','awaiting_contract_approval','generation_queued','generating','cancelling'];
const SUCCESS_JOB_STATUSES=['verified_success'];

function trackedJobIds(){
  try{
    const values=JSON.parse(localStorage.getItem(TRACKED_JOBS_KEY)||'[]');
    return Array.isArray(values)?values.filter(value=>typeof value==='string').slice(0,50):[];
  }catch(_error){ return []; }
}
function persistTrackedJobs(){ localStorage.setItem(TRACKED_JOBS_KEY,JSON.stringify([...trackedJobs.keys()].slice(0,50))); }
function trackJob(job){
  if(!job||!job.id) return;
  trackedJobs.delete(job.id); trackedJobs.set(job.id,job);
  persistTrackedJobs(); $('taskNavCount').textContent=String(trackedJobs.size);
}
function navigatePage(pageId){
  for(const page of document.querySelectorAll('.app-page')) page.classList.toggle('hidden',page.id!==pageId);
  for(const button of document.querySelectorAll('[data-page-target]')) button.classList.toggle('active',button.dataset.pageTarget===pageId);
  if(pageId!=='taskCenterPage') $('resultPanel').classList.add('hidden');
  if(pageId==='taskCenterPage') refreshTaskCenter();
  if(pageId==='topologyPage'){ refreshSystemStatus(); refreshModelStatus(false); }
  history.replaceState(null,'',`#${{topologyPage:'topology',newTaskPage:'new-task',taskCenterPage:'tasks'}[pageId]||'topology'}`);
}

function openJobModal(){ $('jobModal').classList.remove('hidden'); document.body.classList.add('modal-open'); }
function closeJobModal(){ $('jobModal').classList.add('hidden'); document.body.classList.remove('modal-open'); }
function clearApprovalCountdown(){
  if(approvalTimer){ clearTimeout(approvalTimer); approvalTimer=null; }
  approvalJobId=null;
  $('approvalCountdown').textContent='';
}
function startApprovalCountdown(job){
  if(approvalJobId===job.id&&approvalTimer) return;
  clearApprovalCountdown(); approvalJobId=job.id;
  const deadline=Date.now()+APPROVAL_DELAY_MS;
  const tick=()=>{
    if(!currentJob||currentJob.id!==job.id||currentJob.status!=='awaiting_contract_approval'||approvalSubmitting){ clearApprovalCountdown(); return; }
    const seconds=Math.max(0,Math.ceil((deadline-Date.now())/1000));
    $('approvalCountdown').textContent=seconds>0?`${seconds} 秒后自动确认验证契约`:'正在自动确认验证契约……';
    if(seconds===0){ approvalTimer=null; approve(true); }
    else approvalTimer=setTimeout(tick,250);
  };
  tick();
}

function isDownloadableProject(job){ return Boolean(job&&job.request&&job.request.delivery_mode==='downloadable_project'); }
function updateEngineeringApprovalState(){
  if(!currentJob||!isDownloadableProject(currentJob)){ $('approve').disabled=!(currentJob&&currentJob.status==='awaiting_contract_approval'&&currentJob.contract); return; }
  const validName=/^[A-Za-z][A-Za-z0-9_]{0,47}$/.test($('engineeringProjectName').value.trim());
  const acknowledged=$('wiringReviewAck').checked&&$('fieldAcceptanceAck').checked;
  const addresses=[...document.querySelectorAll('#engineeringMappings select[data-field="address"]')].map(item=>item.value);
  const unique=addresses.length===new Set(addresses).size&&addresses.every(Boolean);
  $('engineeringError').textContent=!validName?'工程名称必须以英文字母开头，且仅包含英文字母、数字或下划线。':!unique?'物理地址不能为空或重复。':!acknowledged?'请完成两项工程与现场验收确认。':'';
  $('approve').disabled=!(currentJob.status==='awaiting_contract_approval'&&currentJob.contract&&validName&&unique&&acknowledged);
}
function renderEngineeringTemplate(job){
  const panel=$('engineeringPanel');
  if(!isDownloadableProject(job)||!job.contract||!job.contract.engineering_template){ panel.classList.add('hidden'); engineeringJobId=null; return; }
  panel.classList.remove('hidden');
  if(engineeringJobId===job.id){ updateEngineeringApprovalState(); return; }
  engineeringJobId=job.id;
  const template=job.contract.engineering_template;
  $('engineeringTarget').textContent=template.target||job.request.plc_model;
  $('engineeringProjectName').value=template.project_name||'PLC_APP';
  $('engineeringScanPeriod').value=`${template.scan_period_ms||100} ms`;
  $('engineeringOutputType').value=template.output_electrical_type||'-';
  $('wiringReviewAck').checked=false; $('fieldAcceptanceAck').checked=false;
  const body=$('engineeringMappings'); body.replaceChildren();
  for(const mapping of (template.mappings||[])){
    const row=document.createElement('tr'); row.dataset.symbol=mapping.symbol; row.dataset.direction=mapping.direction; row.dataset.iecType=mapping.iec_type;
    const direction=document.createElement('td'); direction.textContent=mapping.direction==='input'?'输入':'输出';
    const symbol=document.createElement('td'); symbol.className='mapping-symbol'; symbol.textContent=mapping.symbol;
    const description=document.createElement('td'); description.className='mapping-description'; description.textContent=mapping.description||'-';
    const addressCell=document.createElement('td'); const address=document.createElement('select'); address.dataset.field='address';
    const options=mapping.direction==='input'?template.input_addresses:template.output_addresses;
    for(const value of (options||[])){ const option=document.createElement('option'); option.value=value; option.textContent=value; option.selected=value===mapping.address; address.appendChild(option); }
    addressCell.appendChild(address);
    const polarityCell=document.createElement('td'); const polarity=document.createElement('select'); polarity.dataset.field='polarity'; polarity.innerHTML='<option value="high">高电平有效</option><option value="low">低电平有效</option>'; polarity.value=mapping.active_high===false?'low':'high'; polarityCell.appendChild(polarity);
    const safeCell=document.createElement('td'); const safe=document.createElement('select'); safe.dataset.field='safe'; safe.innerHTML='<option value="false">FALSE</option><option value="true">TRUE</option>'; safe.value=String(Boolean(mapping.safe_logical_value)); safeCell.appendChild(safe);
    const noteCell=document.createElement('td'); const note=document.createElement('input'); note.dataset.field='note'; note.maxLength=200; note.placeholder='柜号/端子/线号'; note.value=mapping.terminal_note||''; noteCell.appendChild(note);
    row.append(direction,symbol,description,addressCell,polarityCell,safeCell,noteCell); body.appendChild(row);
  }
  for(const field of panel.querySelectorAll('input,select')) field.addEventListener('input',updateEngineeringApprovalState);
  updateEngineeringApprovalState();
}
function collectEngineeringConfig(){
  const template=currentJob.contract.engineering_template;
  const mappings=[...document.querySelectorAll('#engineeringMappings tr')].map(row=>({
    symbol:row.dataset.symbol,direction:row.dataset.direction,iec_type:row.dataset.iecType,
    address:row.querySelector('[data-field="address"]').value,
    active_high:row.querySelector('[data-field="polarity"]').value==='high',
    safe_logical_value:row.querySelector('[data-field="safe"]').value==='true',
    terminal_note:row.querySelector('[data-field="note"]').value.trim()
  }));
  return {schema_version:1,mode:'downloadable_project',target:template.target,target_profile:template.target_profile,project_name:$('engineeringProjectName').value.trim(),scan_period_ms:Number(template.scan_period_ms),mappings,wiring_review_acknowledged:$('wiringReviewAck').checked,field_acceptance_acknowledged:$('fieldAcceptanceAck').checked};
}

function headers(json=false){
  const value={};
  if(json) value['Content-Type']='application/json';
  return value;
}
async function api(path, options={}){
  const response=await fetch(basePath+path,{...options,credentials:'same-origin',headers:{...headers(Boolean(options.body)),...(options.headers||{})}});
  if(response.status===401){ location.replace(basePath+'/'); throw new Error('登录会话已失效，请重新登录。'); }
  const data=await response.json().catch(()=>({detail:response.statusText}));
  if(!response.ok){
    const error=new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));
    error.status=response.status; error.detail=data.detail; throw error;
  }
  return data;
}
function showMessage(text,error=false){ $('message').textContent=text; $('message').style.color=error?'var(--danger)':''; }
function scheduleReconnect(callback,delay){
  if(pollHandle) clearTimeout(pollHandle);
  pollHandle=setTimeout(()=>{ pollHandle=null; callback(); },delay);
}
function setSystemStatus(label,state='online'){
  const node=$('systemStatus'); node.className=`system-status ${state}`; node.querySelector('span').textContent=label;
}
function setTopologyState(id,state){
  const node=$(id); if(!node) return;
  node.classList.remove('checking','online','warning','offline'); node.classList.add(state);
}
function updateSystemSummary(){
  const selected=modelStatusById.get($('llmModel').value);
  const modelState=!selected?'checking':selected.status==='online'?'online':selected.status==='offline'?'offline':'warning';
  const validatorState=validationOverall===null?'checking':validationOverall?'online':'offline';
  const coreState=modelState==='online'&&validatorState==='online'?'online':modelState==='offline'||validatorState==='offline'?'offline':modelState==='checking'||validatorState==='checking'?'checking':'warning';
  setTopologyState('modelTopologyLink',modelState); setTopologyState('validatorTopologyLink',validatorState); setTopologyState('topologyCore',coreState);
  if(selected&&selected.status==='offline'){ setSystemStatus(`当前模型不可用 · ${selected.label}`,'offline'); return; }
  if(selected&&selected.status==='unconfigured'){ setSystemStatus(`当前模型未配置 · ${selected.label}`,'warning'); return; }
  if(validationOverall===false){ setSystemStatus('部分厂商验证服务不可用','warning'); return; }
  if(validationOverall===true&&selected&&selected.status==='online'){ setSystemStatus('当前模型与验证服务在线','online'); return; }
  setSystemStatus('正在检查生成与验证服务','warning');
}
async function refreshSystemStatus(){
  if(validationStatusBusy) return;
  validationStatusBusy=true;
  try{
    const state=await api('/api/validation-status');
    const host=state.host||{}; const windows=state.windows_worker||{}; const workers=state.windows_workers||[windows]; const controllers=state.controllers||{};
    const hostEndpoint=host.address&&host.port?`${host.address}:${host.port}`:'地址未知';
    setValidatorCard('validationHostStatus',Boolean(host.online),host.online?'宿主机在线':'宿主机不可达',`${hostEndpoint} · ${host.latency_ms||0} ms`);
    const readyWorkers=workers.filter(item=>item&&item.ready).length;
    const connectedWorkers=workers.filter(item=>item&&item.transport_online&&item.heartbeat==='fresh'&&item.worker_heartbeat==='fresh').length;
    const busyWorkers=workers.filter(item=>item&&item.busy).length;
    setValidatorCard('windowsPoolStatus',connectedWorkers>0,connectedWorkers>0?`${connectedWorkers}/${workers.length} 节点已连接`:'连接不可用',`${readyWorkers} 台已准入 · ${Math.max(0,connectedWorkers-readyWorkers)} 台待校验 · ${busyWorkers} 台占用`);
    renderWindowsWorkers(workers);
    const dvp=controllers.DVP48ES300R||{}; const as228=controllers['AS228T-A']||{};
    const allReady=Boolean(host.online&&workers.length===4&&readyWorkers===workers.length&&dvp.ready&&as228.ready);
    validationOverall=allReady; updateSystemSummary();
    const checked=new Date(state.checked_at); $('validatorCheckedAt').textContent=`最近检查：${Number.isNaN(checked.getTime())?'刚刚':checked.toLocaleTimeString()}`;
    $('validatorStatusMessage').textContent=allReady?'4 台 Windows 11 节点均在线，DVP48ES300R 与 AS228T-A 官方验证通道可用。':`当前 ${connectedWorkers}/${workers.length||4} 台节点已连接，${readyWorkers} 台通过准入；系统仅向已准入节点分配任务。`;
  }catch(error){
    for(const id of ['validationHostStatus','windowsPoolStatus']) setValidatorCard(id,false,'状态获取失败','无法连接生产验证状态接口');
    renderWindowsWorkers([]);
    validationOverall=false; $('validatorCheckedAt').textContent='状态检查失败'; $('validatorStatusMessage').textContent='无法读取验证服务器状态，请稍后刷新。'; updateSystemSummary();
  }finally{ validationStatusBusy=false; }
}
function renderWindowsWorkers(workers){
  const grid=$('windowsWorkerGrid'); grid.replaceChildren();
  const values=workers.length?workers:Array.from({length:4},(_,index)=>({name:`vps_windows_${index+1}`,ready:false}));
  for(const [index,item] of values.entries()){
    const card=document.createElement('article');
    const online=Boolean(item.ready); const busy=Boolean(item.busy);
    const connected=Boolean(item.transport_online&&item.heartbeat==='fresh'&&item.worker_heartbeat==='fresh');
    const qualifying=item.admission_state==='qualification';
    card.className=`validator-card topology-node ${online?'ready':connected?'warning':'unavailable'}${busy?' worker-busy':''}`;
    const head=document.createElement('div'); const light=document.createElement('span'); const name=document.createElement('b');
    light.className='status-light'; name.textContent=item.name||`vps_windows_${index+1}`; head.append(light,name);
    const status=document.createElement('strong'); status.textContent=online?(busy?'正在验证':'在线空闲'):connected?(qualifying?'在线待准入校验':'在线但验证组件未就绪'):'离线';
    const endpoint=item.address&&item.port?`${item.address}:${item.port}`:'端点未配置';
    const detail=document.createElement('small');
    detail.textContent=`${endpoint} · ${item.latency_ms||0} ms · ${item.active_target||'DVP / AS'} · 心跳=${item.heartbeat==='fresh'?'正常':'中断'}`;
    const targets=document.createElement('div'); targets.className='worker-target-status';
    const targetDetails=[
      ['DVP48ES300R','COMMGR DVP-ES3 Simulator',Boolean(item.commgr_running&&item.dvp_simulator_running)],
      ['AS228T-A','COMMGR AS200 Simulator',Boolean(item.commgr_running&&item.as200_simulator_running&&item.as228t_template_ready)]
    ];
    for(const [target,simulator,componentsReady] of targetDetails){
      const targetReady=Boolean(item.targets_ready&&item.targets_ready[target]);
      const row=document.createElement('div'); row.className=targetReady?'target-ready':connected&&qualifying&&componentsReady?'target-qualification':'target-unavailable';
      const copy=document.createElement('span');
      const label=document.createElement('b'); label.textContent=target;
      const simulatorLabel=document.createElement('small'); simulatorLabel.textContent=`ISPSoft 3.24 · ${simulator}`;
      copy.append(label,simulatorLabel);
      const value=document.createElement('strong');
      value.textContent=targetReady?'可验证':connected&&qualifying&&componentsReady?'待准入':componentsReady?'等待连接':'组件未就绪';
      row.append(copy,value); targets.appendChild(row);
    }
    card.append(head,status,detail,targets); grid.appendChild(card);
  }
}
function setValidatorCard(id,ready,label,detail){
  const card=$(id); card.classList.remove('checking','ready','unavailable'); card.classList.add(ready?'ready':'unavailable'); card.querySelector('strong').textContent=label; card.querySelector('small').textContent=detail;
}
function renderModelStatus(state){
  modelStatusById=new Map((state.models||[]).map(item=>[item.id,item]));
  for(const option of $('llmModel').options){
    const item=modelStatusById.get(option.value); if(!item) continue;
    option.disabled=item.status!=='online';
    const configured=catalog.models.find(model=>model.id===option.value);
    option.textContent=`${configured?configured.label:option.value}${item.status==='online'?'':'（当前不可用）'}`;
  }
  const grid=$('modelStatusGrid'); grid.replaceChildren();
  for(const item of (state.models||[])){
    const card=document.createElement('article');
    const className=item.status==='online'?'ready':item.status==='offline'?'unavailable':'warning';
    card.className=`validator-card topology-node model-channel-card ${className}`; card.dataset.model=item.id;
    card.classList.toggle('selected',item.id===$('llmModel').value);
    const head=document.createElement('div'); const light=document.createElement('span'); const name=document.createElement('b');
    light.className='status-light'; name.textContent=item.label; head.append(light,name);
    const status=document.createElement('strong');
    status.className='model-channel-state';
    status.textContent=item.status==='online'?'在线可用':item.status==='offline'?'通道不可用':'未配置';
    const protocol=item.api_protocol==='anthropic'?'Anthropic 原生':'OpenAI 兼容';
    const configured=catalog.models.find(model=>model.id===item.id)||{};
    const details=document.createElement('dl'); details.className='model-channel-details';
    const addDetail=(label,value)=>{ const term=document.createElement('dt'); const data=document.createElement('dd'); term.textContent=label; data.textContent=value||'—'; details.append(term,data); };
    addDetail('服务通道',item.provider);
    addDetail('接口地址',configured.base_url||'由服务器配置');
    addDetail('接口协议',protocol);
    addDetail('请求模型',item.requested_model);
    addDetail('响应模型',item.resolved_model||'未返回');
    addDetail('响应延迟',item.latency_ms?`${item.latency_ms} ms`:'未测得');
    const probe=document.createElement('p'); probe.className='model-channel-probe'; probe.textContent=item.detail||'尚未完成在线探测';
    card.append(head,status,details,probe); grid.appendChild(card);
  }
  const checked=new Date(state.checked_at);
  $('modelCheckedAt').textContent=`最近探测：${Number.isNaN(checked.getTime())?'刚刚':checked.toLocaleTimeString()}`;
  const online=(state.models||[]).filter(item=>item.status==='online').length;
  const offline=(state.models||[]).filter(item=>item.status==='offline').length;
  $('modelStatusMessage').textContent=`${online} 个模型在线，${offline} 个通道异常；状态来自最小真实推理，并缓存 ${state.cache_seconds||300} 秒。`;
  updateSystemSummary();
}
async function refreshModelStatus(force=false){
  if(modelStatusBusy) return;
  modelStatusBusy=true; $('refreshModelStatus').disabled=true;
  try{ renderModelStatus(await api(`/api/model-status${force?'?refresh=true':''}`)); }
  catch(error){
    $('modelCheckedAt').textContent='模型状态检查失败';
    $('modelStatusMessage').textContent=`无法读取大模型服务状态：${error.message}`;
    setSystemStatus('大模型状态接口异常','offline');
  }finally{ modelStatusBusy=false; $('refreshModelStatus').disabled=false; }
}
function formatDuration(seconds){
  const value=Math.max(0,Number(seconds)||0); const hours=Math.floor(value/3600); const minutes=Math.floor((value%3600)/60); const secs=Math.floor(value%60);
  return hours?`${String(hours).padStart(2,'0')}:${String(minutes).padStart(2,'0')}:${String(secs).padStart(2,'0')}`:`${String(minutes).padStart(2,'0')}:${String(secs).padStart(2,'0')}`;
}
function renderVendorProcess(state){
  const panel=$('vendorProcessPanel');
  if(!state){ panel.classList.add('hidden'); return; }
  panel.classList.remove('hidden');
  panel.classList.toggle('complete',state.phase==='complete'&&state.result==='pass');
  panel.classList.toggle('failed',state.phase==='complete'&&state.result!=='pass');
  $('vendorProcessTarget').textContent=`${state.target||'台达 PLC'} · vps_windows`;
  $('vendorProcessLabel').textContent=state.phase_label||'正在执行厂商验证';
  $('vendorProcessCase').textContent=state.case_index&&state.case_total?`仿真用例 ${state.case_index}/${state.case_total}`:'';
  const rank=VENDOR_PHASE_RANK[state.phase]??0;
  const flow=$('vendorProcessFlow'); flow.replaceChildren();
  VENDOR_PROCESS_STEPS.forEach((step,index)=>{
    const node=document.createElement('div');
    const isTerminal=state.phase==='complete';
    const isFailed=isTerminal&&state.result!=='pass'&&index===VENDOR_PROCESS_STEPS.length-1;
    const className=isFailed?'failed':isTerminal||index<rank?'done':index===rank?'active':'pending';
    node.className=`vendor-process-step ${className}`;
    const marker=document.createElement('i'); marker.textContent=isFailed?'!':className==='done'?'✓':String(index+1).padStart(2,'0');
    const label=document.createElement('span'); label.textContent=step.label;
    node.append(marker,label); flow.appendChild(node);
  });
}
function describeApiError(error){
  const detail=error&&error.detail;
  if(!detail||typeof detail==='string') return String(detail||error.message||'未知错误');
  const parts=[detail.message||'服务器拒绝了任务'];
  if(Array.isArray(detail.missing)){
    parts.push(...detail.missing.map(item=>`${item.label||item.id}：${item.message||'请补充'}`));
  }
  if(detail.reason) parts.push(`原因：${detail.reason}`);
  if(detail.bridge){
    const b=detail.bridge;
    parts.push(`Windows 桥接=${b.bridge_status||'未知'}`);
    parts.push(`worker=${b.worker_status||'未知'}`);
    parts.push(`COMMGR/模拟器=${b.simulator_status||'未知'}`);
    parts.push(`心跳=${b.heartbeat_fresh?'正常':'中断'}`);
  }
  return parts.join('；');
}
function renderRequirementQuality(result){
  const panel=$('requirementQuality'); panel.replaceChildren(); panel.classList.remove('hidden');
  const heading=document.createElement('b'); heading.textContent=result.message||'需求检查完成'; panel.appendChild(heading);
  const list=document.createElement('ul');
  for(const item of (result.checks||[])){
    const row=document.createElement('li'); row.textContent=`${item.passed?'✓':'✗'} ${item.label}${item.passed?'':'：'+item.detail}`; row.className=item.passed?'quality-pass':'quality-fail'; list.appendChild(row);
  }
  panel.appendChild(list); panel.classList.toggle('quality-ready',Boolean(result.ready)); panel.classList.toggle('quality-missing',!result.ready);
}
async function checkRequirement(){
  if(requirementCheckBusy) return null;
  requirementCheckBusy=true; $('requirementCheck').disabled=true;
  try{
    const result=await api('/api/requirements/check',{method:'POST',body:JSON.stringify({requirement:$('requirement').value})});
    renderRequirementQuality(result); return result;
  }catch(error){ showMessage(describeApiError(error),true); return null; }
  finally{ requirementCheckBusy=false; $('requirementCheck').disabled=false; }
}
function renderProgress(progress){
  openJobModal();
  const awaitingApproval=progress.phase==='awaiting_contract_approval';
  // The contract/engineering form is rendered as the next panel in the same
  // modal.  Hiding the long progress log here prevents it from pushing the
  // required manual I/O review below the visible viewport.
  $('progressPanel').classList.toggle('hidden',awaitingApproval);
  $('progressPhase').textContent=progress.message||'正在处理';
  const contractPhase=String(progress.phase||'').startsWith('contract')||progress.phase==='awaiting_contract_approval';
  const submissionPhase=String(progress.phase||'').startsWith('submission');
  $('progressMessage').textContent=progress.detail_message||(progress.active?'系统正在后台运行，进度会自动更新。':'当前阶段已结束，请查看下方日志。');
  $('progressAttempt').textContent=submissionPhase?'服务预检':contractPhase?`契约 ${progress.contract_attempt||0}/${progress.contract_budget||7}`:`候选 ${progress.current_attempt||0}/${progress.candidate_budget||20}`;
  const delayed=progress.health==='delayed';
  $('progressHint').textContent=delayed?'当前步骤超过通常的无日志时间；系统仍在轮询，若随后返回基础设施错误会在日志中明确显示。':contractPhase?'模型响应通常是本阶段的主要耗时；收到响应后会继续显示结构检查结果。':'PLCverif、OpenPLC 和厂商仿真可能需要数分钟；每个工具开始和结束都会记录。';
  $('progressComponent').textContent=progress.current_component||'任务提交';
  $('progressElapsed').textContent=formatDuration(progress.elapsed_seconds);
  $('progressIdle').textContent=(Number(progress.idle_seconds)||0)<3?'刚刚':`${formatDuration(progress.idle_seconds)} 前`;
  const healthLabels={working:'正常运行',delayed:'等待时间较长',complete:'已经完成',failed:'已经终止'};
  const health=$('progressHealth'); health.textContent=healthLabels[progress.health]||(progress.active?'正常运行':'已经结束');
  health.className=`health-${progress.health||(progress.active?'working':'complete')}`;
  $('progressJobId').textContent=progress.job_id?`JOB ${progress.job_id}`:'任务尚未在服务器创建';
  const percent=Math.max(0,Math.min(100,Number(progress.phase_percent)||0));
  $('progressBar').style.width=`${percent}%`;
  $('progressBar').classList.toggle('active',Boolean(progress.active));
  $('progressBar').parentElement.setAttribute('aria-valuenow',String(percent));
  renderVendorProcess(progress.vendor_visualization||null);
  const log=$('progressLog'); log.replaceChildren();
  for(const item of (progress.events||[]).slice().reverse()){
    const row=document.createElement('li');
    const when=document.createElement('time');
    const detail=document.createElement('span');
    const date=new Date(item.time);
    when.textContent=Number.isNaN(date.getTime())?'--:--:--':date.toLocaleTimeString();
    detail.textContent=item.message; detail.className=item.status||'info';
    row.append(when,detail); log.appendChild(row);
  }
  $('closeProgress').classList.remove('hidden');
  $('cancelJob').classList.toggle('hidden',!progress.active||!currentJob||currentJob.status==='cancelling');
}
async function refreshProgress(jobId){
  try{
    const progress=await api(`/api/jobs/${jobId}/progress`);
    if(currentJob&&currentJob.id===jobId&&currentJob.queue_position&&String(progress.phase).includes('queued')){
      progress.detail_message=`当前位于等待队列第 ${currentJob.queue_position} 位；任一执行槽释放后将自动开始。`;
    }
    renderProgress(progress);
  }
  catch(e){ if(!String(e.message).includes('登录会话')) $('progressMessage').textContent=`进度暂时不可用：${e.message}`; }
}
function renderTaskCenter(capacity=lastTaskCapacity,pagination=historyPagination){
  lastTaskCapacity={...lastTaskCapacity,...capacity}; capacity=lastTaskCapacity;
  historyPagination={...historyPagination,...pagination}; pagination=historyPagination;
  const jobs=[...trackedJobs.values()].sort((a,b)=>String(b.created_at||'').localeCompare(String(a.created_at||'')));
  $('taskSlots').textContent=`${Math.min(Number(capacity.running)||0,Number(capacity.slots)||4)} / ${Number(capacity.slots)||4}`;
  $('taskRunning').textContent=String(Number(capacity.running)||0);
  $('taskQueued').textContent=String(Number(capacity.queued)||0);
  $('taskTracked').textContent=String(Number(pagination.total)||0); $('taskNavCount').textContent=String(Number(pagination.total)||0);
  $('historySummary').textContent=`找到 ${Number(pagination.total)||0} 条记录，本页 ${jobs.length} 条`;
  $('historyPageInfo').textContent=`第 ${Number(pagination.page)||1} / ${Number(pagination.pages)||1} 页`;
  $('historyPrevious').disabled=(Number(pagination.page)||1)<=1;
  $('historyNext').disabled=(Number(pagination.page)||1)>=(Number(pagination.pages)||1);
  const list=$('taskList'); list.replaceChildren(); $('taskEmpty').classList.toggle('hidden',jobs.length>0);
  for(const job of jobs){
    const progress=job.progress_summary||{}; const card=document.createElement('article'); card.className=`task-card${job.archived_at?' archived':''}`; card.tabIndex=0;
    const head=document.createElement('div'); head.className='task-card-head';
    const title=document.createElement('b'); title.textContent=job.request&&job.request.requirement_title||String(job.request&&job.request.requirement||'PLC 控制任务').split(/\r?\n/).find(Boolean)||'PLC 控制任务'; title.title=title.textContent;
    const code=document.createElement('code'); code.textContent=String(job.id).slice(0,8).toUpperCase(); head.append(title,code);
    const meta=document.createElement('div'); meta.className='task-card-meta';
    const target=document.createElement('span'); target.textContent=`${job.request&&job.request.plc_model||'-'} · ${(job.request&&job.request.output_language||'st').toUpperCase()}`;
    const state=document.createElement('span'); state.className=`task-state ${job.status==='verified_success'?'success':ACTIVE_JOB_STATUSES.includes(job.status)?'':'failed'}`; state.textContent=job.archived_at?`已归档 · ${statusLabel(job.status)}`:statusLabel(job.status); meta.append(target,state);
    const bar=document.createElement('div'); bar.className='task-card-progress'; const fill=document.createElement('i'); fill.style.width=`${Math.max(0,Math.min(100,Number(progress.phase_percent)||0))}%`; bar.appendChild(fill);
    const foot=document.createElement('div'); foot.className='task-card-foot';
    const phase=document.createElement('span'); phase.textContent=job.queue_position?`等待队列第 ${job.queue_position} 位`:progress.current_component||progress.message||statusLabel(job.status);
    const created=new Date(job.created_at); const worker=document.createElement('b'); worker.textContent=Number.isNaN(created.getTime())?formatDuration(progress.elapsed_seconds||0):created.toLocaleString(); foot.append(phase,worker);
    const actions=document.createElement('div'); actions.className='task-card-actions';
    if(!ACTIVE_JOB_STATUSES.includes(job.status)){
      const archive=document.createElement('button'); archive.type='button'; archive.textContent=job.archived_at?'恢复':'归档'; archive.addEventListener('click',event=>{ event.stopPropagation(); archiveHistoryJob(job); });
      const remove=document.createElement('button'); remove.type='button'; remove.className='delete-history'; remove.textContent='删除'; remove.addEventListener('click',event=>{ event.stopPropagation(); deleteHistoryJob(job); });
      actions.append(archive,remove);
    }
    card.append(head,meta,bar,foot,actions); card.addEventListener('click',()=>selectTrackedJob(job.id)); card.addEventListener('keydown',event=>{ if(event.key==='Enter'||event.key===' '){ event.preventDefault(); selectTrackedJob(job.id); } }); list.appendChild(card);
  }
}
async function refreshTaskCenter(){
  if(taskCenterBusy) return;
  taskCenterBusy=true;
  try{
    const params=new URLSearchParams({page:String(historyPage),page_size:'12',archive:$('historyArchive').value||'active'});
    if(taskFilter!=='all') params.set('status',taskFilter);
    for(const [id,key] of [['historySearch','search'],['historyPlcModel','plc_model'],['historyLanguage','output_language'],['historyModel','llm_model'],['historyDateFrom','date_from'],['historyDateTo','date_to']]){
      const value=$(id).value.trim(); if(value) params.set(key,value);
    }
    const state=await api(`/api/history?${params}`);
    trackedJobs=new Map((state.jobs||[]).map(job=>[job.id,job]));
    historyPagination=state.pagination||historyPagination;
    $('historyRetention').textContent=state.retention_days?`保留 ${state.retention_days} 天，过期自动归档`:'永久保留，手动归档或删除';
    renderTaskCenter(state.capacity||{},historyPagination);
  }catch(error){ if(!String(error.message).includes('登录会话')) showMessage(`任务中心暂时无法更新：${error.message}`,true); }
  finally{ taskCenterBusy=false; }
}
async function archiveHistoryJob(job){
  const action=job.archived_at?'restore':'archive';
  try{ await api(`/api/history/${job.id}/${action}`,{method:'POST'}); await refreshTaskCenter(); }
  catch(error){ showMessage(`历史记录操作失败：${error.message}`,true); }
}
async function deleteHistoryJob(job){
  if(!confirm(`确定删除“${job.request&&job.request.requirement_title||job.id}”吗？\n任务将从历史中移除，运行工件会进入服务器隔离回收目录。`)) return;
  try{
    await api(`/api/history/${job.id}`,{method:'DELETE'});
    trackedJobs.delete(job.id); persistTrackedJobs();
    if(currentJob&&currentJob.id===job.id){ currentJob=null; $('resultPanel').classList.add('hidden'); }
    await refreshTaskCenter(); showMessage('历史记录已删除，相关工件已移入隔离回收目录。');
  }catch(error){ showMessage(`删除失败：${error.message}`,true); }
}
async function selectTrackedJob(jobId){
  try{
    currentJob=await api(`/api/jobs/${jobId}`); trackJob(currentJob); jobRecovery.save(sessionStorage,currentJob.id); pollFailureCount=0;
    if(ACTIVE_JOB_STATUSES.includes(currentJob.status)){
      openJobModal(); renderJob(currentJob); await refreshProgress(currentJob.id); poll();
    }else{
      closeJobModal(); navigatePage('taskCenterPage'); renderResult(currentJob); $('resultPanel').scrollIntoView({behavior:'smooth',block:'start'});
    }
  }catch(error){ showMessage(`无法打开任务：${error.message}`,true); }
}
function fillModels(){
  const vendor=catalog.vendors.find(v=>v.id===$('vendor').value);
  $('plcModel').innerHTML=vendor.models.map(m=>`<option value="${m.id}">${m.label}</option>`).join('');
  const preferred=vendor.models.find(m=>m.default)||vendor.models[0]; $('plcModel').value=preferred.id; showScope();
}
function showScope(){
  const v=catalog.vendors.find(v=>v.id===$('vendor').value); const m=v.models.find(m=>m.id===$('plcModel').value);
  const nativeLd=v.id==='delta'&&['DVP48ES300R','AS228T-A'].includes(m.id);
  const ldOption=[...$('outputLanguage').options].find(item=>item.value==='ld');
  if(ldOption) ldOption.disabled=!nativeLd;
  if(!nativeLd&&$('outputLanguage').value==='ld') $('outputLanguage').value='st';
  const formatNote=$('outputLanguage').value==='ld'
    ?'梯形图将生成 Ladder IR、SVG、等价 ST 与 ISPSoft 原生 FBU，并经过完整厂商验证。当前开放经校准的布尔触点和普通/置位/复位线圈子集。'
    :'将生成 Structured Text，并经过当前型号对应的验证链。';
  const deliveryNote=$('deliveryMode').value==='downloadable_project'?'成功后还会根据确认的物理 I/O 表生成生产 MAIN，并返回经 ISPSoft 再编译的完整项目包。':'仅交付经过型号验证的功能块，不绑定现场物理地址。';
  $('scope').textContent=`${m.notes} ${formatNote} ${deliveryNote}`;
  document.querySelectorAll('.validator-card[data-controller]').forEach(card=>card.classList.toggle('selected',v.id==='delta'&&card.dataset.controller===m.id));
}
async function loadCatalog(){
  try{
    catalog=await api('/api/catalog');
    $('vendor').innerHTML=catalog.vendors.map(v=>`<option value="${v.id}">${v.label}</option>`).join('');
    $('llmModel').innerHTML=catalog.models.map(m=>`<option value="${m.id}">${m.label}</option>`).join('');
    $('outputLanguage').innerHTML=(catalog.output_languages||[{id:'st',label:'Structured Text（ST）'}]).map(item=>`<option value="${item.id}">${item.label}</option>`).join('');
    $('historyModel').innerHTML='<option value="">全部模型</option>'+catalog.models.map(m=>`<option value="${m.id}">${m.label}</option>`).join('');
    const historyTargets=catalog.vendors.flatMap(v=>v.models.map(m=>({id:m.id,label:`${v.label} · ${m.label}`})));
    $('historyPlcModel').innerHTML='<option value="">全部型号</option>'+historyTargets.map(m=>`<option value="${m.id}">${m.label}</option>`).join('');
    $('vendor').value=catalog.defaults.vendor; $('llmModel').value=catalog.defaults.llm_model; $('outputLanguage').value=catalog.defaults.output_language||'st'; fillModels();
    navigatePage('topologyPage'); refreshSystemStatus(); refreshModelStatus(); await resumeStoredJob(); await refreshTaskCenter();
  }catch(e){ showMessage(`无法加载配置：${e.message}`,true); setSystemStatus('验证服务异常','offline'); }
}
async function submit(){
  if(submissionBusy) return;
  submissionBusy=true; $('submit').disabled=true;
  if(pollHandle){ clearTimeout(pollHandle); pollHandle=null; }
  clearApprovalCountdown(); approvalSubmitting=false; currentJob=null; pollFailureCount=0;
  engineeringJobId=null; $('engineeringPanel').classList.add('hidden');
  jobRecovery.clear(sessionStorage);
  $('approve').disabled=true; $('contract').textContent='';
  $('contractPanel').classList.add('hidden'); $('resultPanel').classList.add('hidden');
  $('ladderPanel').classList.add('hidden'); $('artifactPanel').classList.add('hidden');
  const quality=await checkRequirement();
  if(!quality||!quality.ready){ showMessage(quality?quality.message:'需求检查未完成，请稍后重试。',true); submissionBusy=false; $('submit').disabled=false; return; }
  const started=new Date().toISOString();
  renderProgress({message:'正在连接服务器并检查验证环境',phase:'submission',phase_percent:1,contract_attempt:0,contract_budget:7,current_attempt:0,candidate_budget:Number($('budget').value),active:true,current_component:'服务预检',elapsed_seconds:0,idle_seconds:0,health:'working',events:[{time:started,status:'running',message:'正在检查模型凭据、Linux 验证器和所选控制器的厂商验证 worker'}]});
  showMessage('正在提交需求并生成验证契约……');
  try{
    const body={requirement:$('requirement').value,vendor:$('vendor').value,plc_model:$('plcModel').value,output_language:$('outputLanguage').value,delivery_mode:$('deliveryMode').value,llm_model:$('llmModel').value,max_candidates:Number($('budget').value)};
    const submissionKey=jobRecovery.loadSubmission(sessionStorage)||(globalThis.crypto&&crypto.randomUUID?crypto.randomUUID():`web-${Date.now()}-${Math.random().toString(36).slice(2)}`);
    jobRecovery.saveSubmission(sessionStorage,submissionKey);
    jobRecovery.savePending(sessionStorage,submissionKey,body);
    currentJob=await api('/api/jobs',{method:'POST',headers:{'Idempotency-Key':submissionKey},body:JSON.stringify(body)});
    jobRecovery.clearSubmission(sessionStorage);
    jobRecovery.clearPending(sessionStorage);
    jobRecovery.save(sessionStorage,currentJob.id); trackJob(currentJob); submissionBusy=false; $('submit').disabled=false;
    $('contractPanel').classList.remove('hidden'); renderJob(currentJob); await refreshProgress(currentJob.id); refreshTaskCenter(); poll();
  }catch(e){
    // Keep the key only when no HTTP response arrived: the server may already
    // have created the job and a retry must recover it instead of duplicating it.
    if(e.status){ jobRecovery.clearSubmission(sessionStorage); jobRecovery.clearPending(sessionStorage); }
    const detail=describeApiError(e);
    showMessage(detail,true); submissionBusy=false; $('submit').disabled=false;
    renderProgress({message:'任务未能启动',phase:'submission_failed',phase_percent:100,contract_attempt:0,contract_budget:7,current_attempt:0,candidate_budget:Number($('budget').value),active:false,current_component:'服务预检',elapsed_seconds:Math.max(0,Math.floor((Date.now()-Date.parse(started))/1000)),idle_seconds:0,health:'failed',detail_message:'服务器尚未创建生成任务，因此没有产生模型费用，也没有进入验证契约阶段。',events:[{time:started,status:'running',message:'开始执行服务预检'},{time:new Date().toISOString(),status:'fail',message:detail}]});
  }
}
async function poll(){
  if(!currentJob) return;
  const jobId=currentJob.id;
  try{
    const fresh=await api(`/api/jobs/${jobId}`);
    if(!currentJob||currentJob.id!==jobId) return;
    currentJob={...currentJob,...fresh}; trackJob(currentJob); pollFailureCount=0; renderJob(currentJob); await refreshProgress(jobId); refreshTaskCenter();
  }
  catch(e){
    if(e.status===404){ jobRecovery.clear(sessionStorage); currentJob=null; submissionBusy=false; $('submit').disabled=false; showMessage('服务器中不存在该任务，已清除本地恢复记录。',true); return; }
    pollFailureCount+=1;
    const delay=jobRecovery.reconnectDelay(pollFailureCount);
    showMessage(`网络连接暂时中断，服务器任务不会因页面断网而取消；${Math.ceil(delay/1000)} 秒后自动重连。`,true);
    if(currentJob&&currentJob.id===jobId) scheduleReconnect(poll,delay);
    return;
  }
  const active=['contract_queued','contract_generating','awaiting_contract_approval','generation_queued','generating','cancelling'];
  if(active.includes(currentJob.status)) scheduleReconnect(poll,2000);
}
async function resumeStoredJob(){
  const jobId=jobRecovery.load(sessionStorage);
  const pending=jobRecovery.loadPending(sessionStorage);
  if(!jobId&&!pending) return;
  try{
    if(jobId){
      const recovered=await api(`/api/jobs/${jobId}`); trackJob(recovered);
    }else{
      // A force-refresh may abort the browser after the server accepted POST
      // but before the response arrived. Replaying the exact body with the
      // same idempotency key recovers that job without duplicate model calls.
      const recovered=await api('/api/jobs',{method:'POST',headers:{'Idempotency-Key':pending.key},body:JSON.stringify(pending.request)});
      jobRecovery.save(sessionStorage,recovered.id); trackJob(recovered);
      jobRecovery.clearSubmission(sessionStorage); jobRecovery.clearPending(sessionStorage);
    }
    pollFailureCount=0; showMessage('已恢复刷新前的后台任务，可在任务中心查看。');
  }catch(error){
    if(error.status){ jobRecovery.clearPending(sessionStorage); jobRecovery.clearSubmission(sessionStorage); }
    if(error.status===404){ jobRecovery.clear(sessionStorage); }
    if(!error.status){
      pollFailureCount+=1;
      const delay=jobRecovery.reconnectDelay(pollFailureCount);
      showMessage(`网络暂时不可用，刷新前的任务记录仍在；${Math.ceil(delay/1000)} 秒后自动恢复。`,true);
      scheduleReconnect(resumeStoredJob,delay);
      return;
    }
    showMessage(`无法恢复刷新前的任务：${error.message}`,true);
  }
}
function renderJob(job){
  $('jobStatus').textContent=statusLabel(job.status);
  const canApprove=job.status==='awaiting_contract_approval'&&Boolean(job.contract);
  $('approve').disabled=!canApprove;
  if(job.contract){ const review={...job.contract}; delete review.engineering_template; $('contract').textContent=JSON.stringify(review,null,2); renderEngineeringTemplate(job); }
  else if(['contract_queued','contract_generating'].includes(job.status)){ $('contract').textContent='正在生成并校验验证契约，请稍候……'; }
  if(job.status==='awaiting_contract_approval'){
    openJobModal(); $('contractPanel').classList.remove('hidden');
    if(isDownloadableProject(job)){
      $('contractDetails').open=false;
      clearApprovalCountdown(); $('contractNotice').textContent='请先核对验证契约，再确认下方物理 I/O 映射。涉及真实硬件的地址配置不会自动确认。';
      $('approvalCountdown').textContent='等待人工确认物理 I/O 映射'; showMessage('验证契约已生成；请核对物理 I/O 和现场验收边界后继续。'); updateEngineeringApprovalState();
    }else{
      $('contractDetails').open=true;
      $('contractNotice').textContent='请确认接口、需求、假设、形式性质和测试预期确实表达了你的需求。5 秒内未操作时，系统将自动确认。';
      showMessage('验证契约已生成；可立即确认，或等待 5 秒后自动继续。'); startApprovalCountdown(job);
    }
  }
  if(['generation_queued','generating'].includes(job.status)){ clearApprovalCountdown(); $('contractPanel').classList.add('hidden'); }
  if(job.status==='contract_failed'){ clearApprovalCountdown(); $('contract').textContent=''; showMessage(`验证契约生成失败：${job.last_error||'未知错误'}。请重新提交。`,true); }
  if(job.status==='infrastructure_error'){ clearApprovalCountdown(); showMessage(job.last_error||job.status,true); }
  if(job.status==='cancelling'){ clearApprovalCountdown(); showMessage('正在停止模型调用或验证进程，并保留已生成的证据。'); }
  if(job.status==='cancelled'){ clearApprovalCountdown(); showMessage(job.cancel_reason||'任务已取消。',true); closeJobModal(); }
  if(['verified_success','generation_failed'].includes(job.status)){ clearApprovalCountdown(); closeJobModal(); navigatePage('taskCenterPage'); renderResult(job); }
}
async function approve(automatic=false){
  if(approvalSubmitting) return;
  if(!currentJob||currentJob.status!=='awaiting_contract_approval'||!currentJob.contract){
    showMessage('验证契约尚未生成完成，当前不能确认。',true); return;
  }
  approvalSubmitting=true; clearApprovalCountdown(); $('approve').disabled=true;
  $('approvalCountdown').textContent=automatic?'倒计时结束，正在自动确认……':'正在确认……';
  showMessage('契约已冻结，正在运行生成与验证闭环……');
  try{
    const body={approve:true}; if(isDownloadableProject(currentJob)){ if(automatic) throw new Error('物理 I/O 映射不能自动确认'); body.engineering_config=collectEngineeringConfig(); }
    currentJob=await api(`/api/jobs/${currentJob.id}/approve`,{method:'POST',body:JSON.stringify(body)});
    $('contractPanel').classList.add('hidden'); renderJob(currentJob); await refreshProgress(currentJob.id); poll();
  }
  catch(e){ showMessage(e.message,true); $('approve').disabled=false; $('approvalCountdown').textContent='自动确认失败，请点击按钮重试。'; }
  finally{ approvalSubmitting=false; }
}
async function renderResult(job){
  trackJob(job);
  $('resultPanel').classList.remove('hidden'); $('resultStatus').textContent=statusLabel(job.status);
  const r=job.result||{};
  const vendor=r.vendor_validation||{};
  const delivery=vendor.delivery||{};
  const vendorLabel={passed:'通过',failed:'未通过',inconclusive:'基础设施未完成',not_run:'未执行'}[vendor.status]||'-';
  const language=r.output_language==='ld'?'梯形图（LD）':'Structured Text（ST）';
  const created=new Date(job.created_at); const updated=new Date(job.updated_at);
  $('resultMeta').textContent=`任务 ${job.id} · ${job.request&&job.request.plc_model||'-'} · ${job.request&&job.request.llm_model||'-'} · 创建 ${Number.isNaN(created.getTime())?'-':created.toLocaleString()} · 更新 ${Number.isNaN(updated.getTime())?'-':updated.toLocaleString()}${job.archived_at?' · 已归档':''}`;
  $('metrics').innerHTML=[['验证结果',r.success?'通过':'未通过'],['程序类型',language],['候选数',`${r.candidates_used||0}/${r.candidate_budget||0}`],['模型',r.requested_model||'-'],['厂商验证',vendorLabel],['交付等级',delivery.status==='compiled_downloadable_project'?'可下载 ISPSoft 工程':'验证功能块']].map(([k,v])=>`<div class="metric">${k}<b>${v}</b></div>`).join('');
  $('program').textContent=job.final_program||'没有获得可显示的候选程序。'; $('error').textContent=job.last_error||'';
  $('resultContract').textContent=job.contract?JSON.stringify(job.contract,null,2):'该任务没有可显示的验证契约。';
  $('programLabel').textContent=r.output_language==='ld'?'梯形图源文件（Ladder IR）':'最终候选程序';
  const links=$('artifactLinks'); links.replaceChildren();
  for(const artifact of (r.artifacts||[])){
    const link=document.createElement('a'); link.href=basePath+artifact.url; link.textContent=artifact.label; link.setAttribute('download',''); links.appendChild(link);
  }
  $('artifactPanel').classList.toggle('hidden',!(r.artifacts||[]).length);
  $('ladderPanel').classList.add('hidden');
  if(ladderBlobUrl){ URL.revokeObjectURL(ladderBlobUrl); ladderBlobUrl=null; }
  const svgArtifact=(r.artifacts||[]).find(item=>item.kind==='ld-svg');
  if(svgArtifact){
    try{
      const response=await fetch(basePath+svgArtifact.url,{credentials:'same-origin'});
      if(response.ok){ ladderBlobUrl=URL.createObjectURL(await response.blob()); $('ladderDiagram').src=ladderBlobUrl; $('ladderPanel').classList.remove('hidden'); }
    }catch(_error){ /* Source and download links remain available. */ }
  }
  const vendorPassed=vendor.status==='passed';
  const vendorTarget=vendor.target||'所选控制器';
  showMessage(r.success?(vendorPassed?`已通过 MatIEC、PLCverif、OpenPLC，以及 ISPSoft/COMMGR ${vendorTarget} 厂商验证。`:'已通过确认契约下的 MatIEC、PLCverif 和 OpenPLC 验证。'):`未能在当前候选预算内通过全部验证；确定性反馈已用于后续${r.output_language==='ld'?'梯形图':' ST'}候选修正。`,!r.success);
  submissionBusy=false; $('submit').disabled=false;
}

$('vendor').addEventListener('change',fillModels); $('plcModel').addEventListener('change',showScope); $('outputLanguage').addEventListener('change',showScope); $('deliveryMode').addEventListener('change',showScope);
$('llmModel').addEventListener('change',()=>{
  document.querySelectorAll('.validator-card[data-model]').forEach(card=>card.classList.toggle('selected',card.dataset.model===$('llmModel').value));
  updateSystemSummary();
});
$('submit').addEventListener('click',submit); $('approve').addEventListener('click',()=>approve(false)); $('requirementCheck').addEventListener('click',checkRequirement); loadCatalog();
for(const button of document.querySelectorAll('[data-page-target]')) button.addEventListener('click',()=>navigatePage(button.dataset.pageTarget));
$('newTaskFromCenter').addEventListener('click',()=>navigatePage('newTaskPage'));
for(const button of document.querySelectorAll('[data-task-filter]')) button.addEventListener('click',()=>{
  taskFilter=button.dataset.taskFilter; historyPage=1; for(const item of document.querySelectorAll('[data-task-filter]')) item.classList.toggle('active',item===button); refreshTaskCenter();
});
$('applyHistoryFilters').addEventListener('click',()=>{ historyPage=1; refreshTaskCenter(); });
$('resetHistoryFilters').addEventListener('click',()=>{
  for(const id of ['historySearch','historyPlcModel','historyLanguage','historyModel','historyDateFrom','historyDateTo']) $(id).value='';
  $('historyArchive').value='active'; taskFilter='all'; historyPage=1;
  for(const item of document.querySelectorAll('[data-task-filter]')) item.classList.toggle('active',item.dataset.taskFilter==='all');
  refreshTaskCenter();
});
$('historySearch').addEventListener('keydown',event=>{ if(event.key==='Enter'){ event.preventDefault(); historyPage=1; refreshTaskCenter(); } });
$('historyPrevious').addEventListener('click',()=>{ if(historyPage>1){ historyPage-=1; refreshTaskCenter(); } });
$('historyNext').addEventListener('click',()=>{ if(historyPage<(historyPagination.pages||1)){ historyPage+=1; refreshTaskCenter(); } });
$('closeProgress').addEventListener('click',()=>{ clearApprovalCountdown(); closeJobModal(); currentJob=null; navigatePage('taskCenterPage'); });
$('refreshValidationStatus').addEventListener('click',refreshSystemStatus);
$('refreshModelStatus').addEventListener('click',()=>refreshModelStatus(true));
$('cancelJob').addEventListener('click',async()=>{
  if(!currentJob||!confirm('确认取消当前任务？已完成的候选和验证证据会保留。')) return;
  $('cancelJob').disabled=true;
  try{
    currentJob=await api(`/api/jobs/${currentJob.id}/cancel`,{method:'POST'});
    trackJob(currentJob); renderJob(currentJob); await refreshProgress(currentJob.id); refreshTaskCenter(); poll();
  }catch(error){ showMessage(`取消任务失败：${error.message}`,true); }
  finally{ $('cancelJob').disabled=false; }
});
setInterval(refreshSystemStatus,15000);
setInterval(()=>refreshModelStatus(false),60000);
setInterval(refreshTaskCenter,2500);
$('logout').addEventListener('click',async()=>{
  jobRecovery.clear(sessionStorage); jobRecovery.clearSubmission(sessionStorage); jobRecovery.clearPending(sessionStorage);
  localStorage.removeItem(TRACKED_JOBS_KEY);
  await fetch(basePath+'/api/logout',{method:'POST',credentials:'same-origin'}); location.replace(basePath+'/');
});
