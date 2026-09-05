import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

st.set_page_config(page_title='RecoverAI | Revenue Recovery', page_icon='◈', layout='wide', initial_sidebar_state='expanded')
BASE_DIR = Path(__file__).resolve().parent
RESULT_FILE = BASE_DIR / 'recovery_results.csv'
VALID_ACTIONS = ['RETRY','REMINDER','UPDATE_PAYMENT','ESCALATE','STOP']

st.markdown('''<style>
.block-container{padding-top:1.5rem;padding-bottom:3rem;max-width:1500px}
[data-testid="stSidebar"]{border-right:1px solid rgba(255,255,255,.08)}
.brand{padding:.4rem 0 1.2rem}.brand-title{font-size:1.55rem;font-weight:800}.brand-sub{color:#8b949e;font-size:.74rem}
.page-title{font-size:2rem;font-weight:800;letter-spacing:-1px}.page-subtitle{color:#8b949e;margin-bottom:1.4rem}
.section-title{font-size:1.05rem;font-weight:750;margin:.2rem 0 .8rem}
.kpi{border:1px solid rgba(255,255,255,.09);border-radius:14px;padding:1rem 1.05rem;background:linear-gradient(145deg,rgba(255,255,255,.045),rgba(255,255,255,.015));min-height:112px}
.kpi-label{color:#8b949e;font-size:.76rem;text-transform:uppercase;letter-spacing:.5px}.kpi-value{font-size:1.65rem;font-weight:800;margin-top:.45rem}.kpi-note{color:#8b949e;font-size:.72rem;margin-top:.35rem}
.panel{border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:1rem 1.1rem;background:rgba(255,255,255,.018);margin-bottom:1rem}
.status-pill{display:inline-block;padding:.28rem .65rem;border-radius:999px;font-size:.72rem;font-weight:700;background:rgba(34,197,94,.10);border:1px solid rgba(34,197,94,.25)}
.success-box,.warning-box,.danger-box,.info-box{padding:.8rem 1rem;border-radius:9px;margin:.4rem 0}.success-box{border-left:4px solid #22c55e;background:rgba(34,197,94,.08)}.warning-box{border-left:4px solid #f59e0b;background:rgba(245,158,11,.08)}.danger-box{border-left:4px solid #ef4444;background:rgba(239,68,68,.08)}.info-box{border-left:4px solid #60a5fa;background:rgba(96,165,250,.08)}
.rule{padding:.65rem .8rem;border:1px solid rgba(255,255,255,.07);border-radius:9px;margin-bottom:.45rem;background:rgba(255,255,255,.018)}
.metric-big{font-size:1.8rem;font-weight:800}.muted{color:#8b949e;font-size:.8rem}
</style>''', unsafe_allow_html=True)

@st.cache_data
def load_results():
    if not RESULT_FILE.exists(): return None
    df=pd.read_csv(RESULT_FILE).dropna(how='all').copy()
    nums=['amount','recovery_probability','confidence','recovered_amount','previous_success','previous_failures','recovery_attempts']
    for c in nums:
        if c in df: df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0)
    defaults={'recommended_action':'ERROR','error':'','outcome':'','failure_reason':'','transaction_id':'','customer_id':'','status':'','recovery_probability':0.0,'confidence':0.0,'recovered_amount':0.0,'recovery_attempts':0,'previous_success':0,'previous_failures':0,'subscription_active':'','recovery_action':'','recovery_status':''}
    for c,v in defaults.items():
        if c not in df: df[c]=v
    for c in ['recommended_action','outcome','failure_reason','status','error','transaction_id','customer_id','subscription_active','recovery_action','recovery_status']: df[c]=df[c].fillna('').astype(str)
    df['recommended_action']=df['recommended_action'].str.upper().str.strip(); df['outcome']=df['outcome'].str.upper().str.strip(); df['status']=df['status'].str.upper().str.strip(); df['failure_reason']=df['failure_reason'].str.lower().str.strip()
    for c in ['amount','recovery_probability','confidence','recovered_amount','recovery_attempts','previous_success','previous_failures']:
        df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0)
    df['amount']=df['amount'].clip(lower=0)
    df['recovery_probability']=df['recovery_probability'].clip(0,1)
    df['confidence']=df['confidence'].clip(0,1)
    df['recovered_amount']=df['recovered_amount'].clip(lower=0)
    df['recovery_probability']=pd.to_numeric(df['recovery_probability'],errors='coerce').clip(0,1).fillna(0)
    df['confidence']=pd.to_numeric(df['confidence'],errors='coerce').clip(0,1).fillna(0)
    df['recovered_amount']=pd.to_numeric(df['recovered_amount'],errors='coerce').clip(lower=0).fillna(0)
    mask=df['outcome'].eq('RECOVERED') & df['recovered_amount'].le(0); df.loc[mask,'recovered_amount']=df.loc[mask,'amount']
    return df

df=load_results()
if df is None:
    st.title('RecoverAI'); st.error('recovery_results.csv was not found.'); st.code('python batch_processor.py\nstreamlit run app.py'); st.stop()

unrecoverable=df[df.failure_reason.eq('insufficient_funds')].copy(); failed=df[df.status.eq('FAILED')].copy(); risk_cases=failed[~failed.index.isin(unrecoverable.index)].copy()
unrecoverable_amount=float(unrecoverable.amount.sum()); revenue_at_risk=float(risk_cases.amount.sum()); revenue_recovered=float(df.recovered_amount.sum()); recovery_rate=revenue_recovered/revenue_at_risk*100 if revenue_at_risk else 0
recovered_cases=int(df.outcome.eq('RECOVERED').sum()); reminder_cases=df[df.recommended_action.eq('REMINDER')].copy(); recovery_failed=df[df.outcome.eq('RECOVERY_FAILED')].copy()
ai_error_cases=df[(df.recommended_action.isin(['ERROR',''])) | df.error.str.strip().ne('')].copy(); ai_error_cases=ai_error_cases[~ai_error_cases.outcome.eq('RECOVERED')]
reminder_amount=float(reminder_cases.amount.sum()); recovery_failed_amount=float(recovery_failed.amount.sum()); ai_error_amount=float(ai_error_cases.amount.sum()); valid_cases=df[df.recommended_action.isin(VALID_ACTIONS)].copy(); escalated_cases=int(df.recommended_action.eq('ESCALATE').sum())
pending_actionable_amount=max(revenue_at_risk-revenue_recovered,0)

def money(x): return f'₹{float(x):,.2f}'
def header(title,sub): st.markdown(f'<div class="page-title">{title}</div><div class="page-subtitle">{sub}</div>',unsafe_allow_html=True)
def kpis(items):
    cols=st.columns(len(items))
    for col,(label,value,note) in zip(cols,items):
        with col: st.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>',unsafe_allow_html=True)
def explanation(row):
    a=str(row.recommended_action); r=str(row.failure_reason or 'unknown'); p=int(float(row.get('previous_success',0))); n=int(float(row.get('recovery_attempts',0)))
    if a=='RETRY': return f'The agent selected RETRY because {r} is potentially recoverable. The customer has {p} previous successful payment(s) and {n} previous recovery attempt(s).','success-box'
    if a=='REMINDER': return f'The agent selected REMINDER because {r} may require customer attention before another payment attempt.','warning-box'
    if a=='UPDATE_PAYMENT': return 'The agent selected UPDATE_PAYMENT because the payment method may be expired or require replacement.','warning-box'
    if a=='ESCALATE': return 'The agent selected ESCALATE because the case requires additional intervention rather than another automatic attempt.','warning-box'
    if a=='STOP': return 'The agent selected STOP because continuing automated recovery would violate the bounded recovery policy.','danger-box'
    if r=='insufficient_funds': return 'This case is UNRECOVERABLE because automated recovery cannot succeed without additional customer funds.','danger-box'
    return 'The transaction did not receive a usable AI recovery decision.','info-box'

with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-title">◈ RecoverAI</div><div class="brand-sub">AI REVENUE RECOVERY CONTROL CENTER</div></div>',unsafe_allow_html=True)

    GENERAL_PAGES = ['Overview','Recovery Intelligence','AI Detection','Transactions']
    GOVERNANCE_PAGES = ['Audit Trail','System Safety']

    if 'recoverai_page' not in st.session_state:
        st.session_state.recoverai_page = 'Overview'

    def nav_button(label):
        if st.button(label, key=f'nav_{label}', use_container_width=True,
                     type='primary' if st.session_state.recoverai_page == label else 'secondary'):
            st.session_state.recoverai_page = label
            st.rerun()

    st.markdown('### GENERAL')
    for item in GENERAL_PAGES:
        nav_button(item)

    st.markdown('### GOVERNANCE')
    for item in GOVERNANCE_PAGES:
        nav_button(item)

    page = st.session_state.recoverai_page

    st.divider()
    st.markdown('<span class="status-pill">● AI AGENT ACTIVE</span>',unsafe_allow_html=True)
    st.caption('Virtual payment environment')
    st.caption(f'{len(df):,} transactions in latest batch')
    if st.button('↻ Refresh Data',use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if page=='Overview':
    header('Overview','Executive view of revenue exposure, recovery performance, and agent activity.')
    kpis([('Revenue At Risk',money(revenue_at_risk),'Actionable failed-payment value'),('Revenue Recovered',money(revenue_recovered),f'{recovered_cases} successful recoveries'),('Recovery Rate',f'{recovery_rate:.1f}%','Recovered ÷ actionable risk'),('Unrecoverable',money(unrecoverable_amount),'Insufficient-funds cases'),('Transactions',f'{len(df):,}','Latest batch processed')])
    st.write(''); l,r=st.columns([1.25,1])
    with l:
        st.markdown('<div class="section-title">Recovery Funnel</div>',unsafe_allow_html=True)
        funnel=pd.DataFrame({'Stage':['Failed Payments','Actionable Risk','Recovered','Unrecoverable'],'Amount':[failed.amount.sum(),revenue_at_risk,revenue_recovered,unrecoverable_amount]}).set_index('Stage'); st.bar_chart(funnel,height=310); st.caption(f'{money(unrecoverable_amount)} of failed value is classified as unrecoverable and excluded from the recovery-rate denominator.')
    with r:
        st.markdown('<div class="section-title">Agent Actions</div>',unsafe_allow_html=True)
        counts=df.recommended_action.replace('','ERROR').value_counts(); order=['RETRY','REMINDER','UPDATE_PAYMENT','ESCALATE','STOP','ERROR','NOT_REQUIRED']; counts=counts.reindex([x for x in order if x in counts.index]).fillna(0).astype(int); st.bar_chart(counts,height=310)
    l,r=st.columns(2)
    with l:
        st.markdown('<div class="section-title">Outcome Summary</div>',unsafe_allow_html=True); escalated_df=df[df['recommended_action'].eq('ESCALATE')].copy(); escalated_amount=float(escalated_df['amount'].sum()); escalated_count=len(escalated_df); o=pd.DataFrame({'Outcome':['Recovered','Reminder','Recovery Failed','AI Error','Escalated','Unrecoverable'],'Cases':[recovered_cases,len(reminder_cases),len(recovery_failed),len(ai_error_cases),escalated_count,len(unrecoverable)],'Amount':[revenue_recovered,reminder_amount,recovery_failed_amount,ai_error_amount,escalated_amount,unrecoverable_amount]}); o['Amount']=o.Amount.map(money); st.dataframe(o,use_container_width=True,hide_index=True)
    with r:
        st.markdown('<div class="section-title">High Priority Recovery Queue</div>',unsafe_allow_html=True); q=valid_cases[valid_cases.outcome.ne('RECOVERED') & ~valid_cases.index.isin(unrecoverable.index)].sort_values(['recovery_probability','amount'],ascending=False).head(8)
        if len(q):
            v=q[['transaction_id','amount','failure_reason','recovery_probability','recommended_action']].copy(); v['amount']=v.amount.map(money); v['recovery_probability']=(v.recovery_probability*100).round(1).astype(str)+'%'; st.dataframe(v,use_container_width=True,hide_index=True)
        else: st.success('No pending high-priority actionable cases.')

elif page=='Recovery Intelligence':
    header('Recovery Intelligence','Understand where revenue is at risk and which failure types offer the strongest recovery opportunity.')
    kpis([('Actionable Revenue',money(revenue_at_risk),'Excluded: insufficient funds'),('Pending Opportunity',money(pending_actionable_amount),'Actionable value not yet recovered'),('Recovered',money(revenue_recovered),'Actual simulated recovery'),('Recovery Rate',f'{recovery_rate:.1f}%','Recovered ÷ actionable risk')])
    st.write(''); reason=failed.copy()
    if len(reason):
        s=reason.groupby('failure_reason').agg(Cases=('amount','size'),At_Risk=('amount','sum'),Recovered=('recovered_amount','sum')).reset_index(); s['Recovery Rate']=np.where(s.At_Risk>0,s.Recovered/s.At_Risk*100,0)
        l,r=st.columns(2)
        with l: st.markdown('<div class="section-title">Revenue Exposure by Failure Reason</div>',unsafe_allow_html=True); st.bar_chart(s.set_index('failure_reason')[['At_Risk','Recovered']],height=330)
        with r: st.markdown('<div class="section-title">Recovery Effectiveness</div>',unsafe_allow_html=True); st.bar_chart(s.set_index('failure_reason')[['Recovery Rate']],height=330)
        t=s.copy(); t['At_Risk']=t.At_Risk.map(money); t['Recovered']=t.Recovered.map(money); t['Recovery Rate']=t['Recovery Rate'].round(1).astype(str)+'%'; t=t.rename(columns={'failure_reason':'Failure Reason','At_Risk':'At Risk'}); st.dataframe(t[['Failure Reason','Cases','At Risk','Recovered','Recovery Rate']],use_container_width=True,hide_index=True)
    st.markdown('<div class="section-title">Recovery Opportunity Ranking</div>',unsafe_allow_html=True); q=risk_cases.copy(); q['Opportunity']=q.amount*q.recovery_probability; q=q.sort_values('Opportunity',ascending=False).head(10)
    if len(q):
        v=q[['transaction_id','amount','failure_reason','recovery_probability','recommended_action','Opportunity']].copy(); v['amount']=v.amount.map(money); v['Opportunity']=v.Opportunity.map(money); v['recovery_probability']=(v.recovery_probability*100).round(1).astype(str)+'%'; st.dataframe(v,use_container_width=True,hide_index=True)
    else: st.success('No actionable recovery opportunities.')

elif page=='AI Detection':
    header('AI Detection','Inspect how the AI agent diagnoses failed payments and selects bounded recovery actions.')
    ai=failed.copy(); valid=len(ai[ai.recommended_action.isin(VALID_ACTIONS)]); avgp=ai.recovery_probability.mean()*100 if len(ai) else 0; avgc=ai.confidence.mean()*100 if len(ai) else 0
    kpis([('Transactions Analyzed',f'{len(ai):,}','Failed payments sent to decision layer'),('Valid Decisions',f'{valid:,}','Approved action vocabulary'),('Policy-Compliant',f'{valid:,}','Passed bounded action check'),('AI Errors',f'{len(ai_error_cases):,}','Unusable AI decisions'),('Avg Probability',f'{avgp:.1f}%','Across failed transactions')])
    st.write(''); l,r=st.columns(2)
    with l:
        st.markdown('<div class="section-title">Decision Distribution</div>',unsafe_allow_html=True); c=ai.recommended_action.replace('','ERROR').value_counts(); order=['RETRY','REMINDER','UPDATE_PAYMENT','ESCALATE','STOP','ERROR']; c=c.reindex([x for x in order if x in c.index]).fillna(0).astype(int); st.bar_chart(c,height=320)
    with r:
        st.markdown('<div class="section-title">AI Confidence & Recovery Probability</div>',unsafe_allow_html=True); st.line_chart(ai[['recovery_probability','confidence']].reset_index(drop=True).head(30),height=320); st.caption(f'Average confidence: {avgc:.1f}% across analyzed failed transactions.')
    st.markdown('<div class="section-title">Agent Investigation</div>',unsafe_allow_html=True)
    if len(df):
        tx=st.selectbox('Select a transaction',df['transaction_id'].astype(str).tolist(),key='ai_tx'); row=df[df['transaction_id'].astype(str).eq(tx)].iloc[0]; amount=float(row.get('amount',0) or 0); action=str(row.get('recommended_action','ERROR') or 'ERROR'); prob=float(row.get('recovery_probability',0) or 0); conf=float(row.get('confidence',0) or 0); outcome=str(row.get('outcome','PENDING') or 'PENDING'); recovered=float(row.get('recovered_amount',0) or 0)
        a,b,c,d,e=st.columns(5); a.metric('Amount',money(amount)); b.metric('AI Action',action); c.metric('Recovery Probability',f'{prob*100:.1f}%'); d.metric('Confidence',f'{conf*100:.1f}%'); e.metric('Outcome',outcome)
        msg,box=explanation(row); st.markdown(f'<div class="{box}">{msg}</div>',unsafe_allow_html=True); l,r=st.columns(2)
        with l:
            details={'Transaction ID':row.get('transaction_id','N/A'),'Customer ID':row.get('customer_id','N/A'),'Amount':money(amount),'Status':row.get('status','N/A'),'Failure Reason':row.get('failure_reason','') or 'N/A','Previous Successful Payments':row.get('previous_success',0),'Previous Failures':row.get('previous_failures',0),'Recovery Attempts':row.get('recovery_attempts',0),'Recovery Status':outcome,'Amount Recovered':money(recovered)}; st.dataframe(pd.DataFrame(list(details.items()),columns=['Field','Value']),use_container_width=True,hide_index=True)
        with r:
            st.markdown('#### Decision Pipeline');
            for x in ['1. Detect failed payment','2. Retrieve transaction & customer context','3. Diagnose failure reason','4. Generate AI recovery recommendation','5. Validate action against bounded policy','6. Execute only an approved recovery action','7. Record outcome in audit trail']: st.markdown(f'<div class="rule">{x}</div>',unsafe_allow_html=True)

elif page=='Transactions':
    header('Transactions','Search, filter, and inspect every transaction processed by the latest recovery batch.')
    a,b,c,d=st.columns(4)
    status=a.selectbox('Status',['All','FAILED','SUCCESS'],index=0); outcome=b.selectbox('Outcome',['All','RECOVERED','RECOVERY_FAILED','NOT_REQUIRED','REMINDER_SENT','ESCALATED','AI_ERROR','PENDING'],index=0); action=c.selectbox('AI Action',['All']+VALID_ACTIONS+['ERROR','NOT_REQUIRED'],index=0); search=d.text_input('Search transaction/customer',placeholder='TX-00 or C10...')
    v=df.copy();
    if status!='All': v=v[v.status.eq(status)]
    if outcome!='All': v=v[v.outcome.eq(outcome)]
    if action!='All': v=v[v.recommended_action.eq(action)]
    if search.strip(): q=search.strip().lower(); v=v[v.transaction_id.str.lower().str.contains(q,na=False)|v.customer_id.str.lower().str.contains(q,na=False)]
    st.caption(f'Showing {len(v):,} of {len(df):,} transactions'); cols=[x for x in ['transaction_id','customer_id','amount','failure_reason','recommended_action','recovery_probability','recovery_attempts','outcome','recovered_amount'] if x in v]; t=v[cols].copy(); t['amount']=t.amount.map(money); t['recovered_amount']=t.recovered_amount.map(money); t['recovery_probability']=(t.recovery_probability*100).round(1).astype(str)+'%'; st.dataframe(t,use_container_width=True,hide_index=True,height=500)
    if len(v):
        st.markdown('#### Transaction Detail'); tx=st.selectbox('Open transaction',v.transaction_id.astype(str).tolist(),key='detail'); row=v[v.transaction_id.astype(str).eq(tx)].iloc[0]; a,b,c,d=st.columns(4); a.metric('Amount',money(row.amount)); b.metric('Failure',row.failure_reason or 'None'); c.metric('AI Action',row.recommended_action); d.metric('Outcome',row.outcome or 'PENDING'); st.markdown(f'<div class="info-box"><b>{tx}</b> — customer {row.customer_id} — recovered {money(row.recovered_amount)} from {money(row.amount)}.</div>',unsafe_allow_html=True)

elif page=='Audit Trail':
    header('Audit Trail','Trace the decision lifecycle from failed payment detection through recovery outcome.')
    kpis([('Decisions Recorded',f'{len(df):,}','One record per processed transaction'),('Recovered Events',f'{recovered_cases:,}','Successful recovery outcomes'),('Escalations',f'{escalated_cases:,}','Requires additional intervention'),('AI Errors',f'{len(ai_error_cases):,}','Unusable AI decisions')])
    st.write(''); tx=st.selectbox('Select transaction for audit',df['transaction_id'].astype(str).tolist(),key='audit_tx'); row=df[df['transaction_id'].astype(str).eq(tx)].iloc[0]; action=str(row.get('recommended_action','ERROR') or 'ERROR'); outcome=str(row.get('outcome','PENDING') or 'PENDING'); reason=str(row.get('failure_reason','unknown') or 'unknown'); prob=float(row.get('recovery_probability',0) or 0); attempts=int(float(row.get('recovery_attempts',0) or 0)); amount=float(row.get('amount',0) or 0); recovered=float(row.get('recovered_amount',0) or 0)
    st.markdown('### Decision Timeline')
    timeline=[('01','TRANSACTION DETECTED',f'{tx} · {money(amount)}'),('02','FAILURE CLASSIFIED',reason),('03','AI DECISION',f'{action} · probability {prob*100:.1f}%'),('04','POLICY VALIDATION','Approved action vocabulary and stopping rules checked'),('05','RECOVERY EXECUTION',f'Attempts recorded: {attempts}'),('06','OUTCOME RECORDED',f'{outcome} · recovered {money(recovered)}')]
    for n,title,detail in timeline: st.markdown(f'<div class="panel"><div class="muted">{n}</div><div style="font-weight:800;margin:.2rem 0">{title}</div><div class="muted">{detail}</div></div>',unsafe_allow_html=True)
    st.markdown('### Recorded Decision Data'); cols=[c for c in ['transaction_id','customer_id','amount','status','failure_reason','recommended_action','recovery_probability','confidence','recovery_attempts','outcome','recovered_amount','error'] if c in row.index]; st.dataframe(pd.DataFrame({'Field':cols,'Value':[row[c] for c in cols]}),use_container_width=True,hide_index=True)

else:
    header('System Safety','AI recommendations are bounded by deterministic recovery rules before any recovery action is executed.')
    invalid=int((~df.recommended_action.isin(VALID_ACTIONS+['ERROR','NOT_REQUIRED',''])).sum()); over=int((df.recovery_attempts>3).sum()); negative=int((df.recovered_amount<0).sum()); insuff=int(unrecoverable.recovered_amount.gt(0).sum())
    kpis([('Policy Violations',f'{invalid+over:,}','Invalid actions + attempt breaches'),('Invalid Actions',f'{invalid:,}','Outside approved vocabulary'),('Attempt Breaches',f'{over:,}','More than 3 recovery attempts'),('Insufficient Recovered',f'{insuff:,}','Should always remain unrecoverable'),('Negative Recovery',f'{negative:,}','Financial integrity check')])
    l,r=st.columns(2)
    with l:
        st.markdown('### Recovery Guardrails'); rules=['Maximum 3 automated recovery attempts','Only approved recovery actions are allowed','Expired cards → UPDATE_PAYMENT','Authentication / payment-limit → REMINDER','Temporary / network failures → RETRY','Insufficient funds → UNRECOVERABLE','Repeated failures → STOP / ESCALATE','Every AI decision is recorded'];
        for rule in rules: st.markdown(f'<div class="rule"><b>✓ PASS</b>&nbsp;&nbsp;{rule}</div>',unsafe_allow_html=True)
    with r:
        st.markdown('### Agent Permission Boundary'); st.markdown('<div class="panel"><div class="muted">AI DECISION LAYER</div><div class="metric-big">Recommend</div><div style="text-align:center;font-size:1.4rem">↓</div><div class="muted">BOUNDED POLICY</div><div class="metric-big">Validate</div><div style="text-align:center;font-size:1.4rem">↓</div><div class="muted">RECOVERY ENGINE</div><div class="metric-big">Execute</div><div style="text-align:center;font-size:1.4rem">↓</div><div class="muted">AUDIT TRAIL</div><div class="metric-big">Record</div></div>',unsafe_allow_html=True)
    if invalid==0 and over==0 and insuff==0 and negative==0: st.markdown('<div class="success-box"><b>Safety checks are clean.</b> No invalid actions, attempt-limit breaches, recovered insufficient-funds cases, or negative recovery amounts were found.</div>',unsafe_allow_html=True)
    else: st.markdown('<div class="warning-box"><b>Review required.</b> One or more safety counters require investigation.</div>',unsafe_allow_html=True)
    st.markdown('### Financial Accounting Boundary'); st.markdown(f'<div class="info-box"><b>Revenue At Risk:</b> {money(revenue_at_risk)}<br>Insufficient-funds failures are classified separately as <b>UNRECOVERABLE</b> and excluded from the risk denominator.<br><br><b>Revenue Recovered:</b> {money(revenue_recovered)}<br>Recovery is counted from recorded recovered amounts.</div>',unsafe_allow_html=True)