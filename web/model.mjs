export const SCHEMA = 'coolcode.browserreceipt.v1';
export const STORAGE = 'coolcode:browserreceipt:baseline:v1';
export const displayValue = value => value == null ? 'Not exposed' : typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value);
export function compareReceipts(before, after) {
 const a=before?.values||{}, b=after?.values||{};
 return [...new Set([...Object.keys(a),...Object.keys(b)])].sort().filter(k=>JSON.stringify(a[k])!==JSON.stringify(b[k])).map(key=>({key,before:displayValue(a[key]),after:displayValue(b[key])}));
}
export function validateReceipt(value) {
 if(!value||value.schema!==SCHEMA||typeof value.capturedAt!=='string'||!Number.isFinite(Date.parse(value.capturedAt))||!value.values||Array.isArray(value.values)||typeof value.values!=='object')throw new Error('This is not a Browser Receipt export.');
 const entries=Object.entries(value.values);
 if(entries.length>120||entries.some(([k,v])=>k.length>100||!['string','number','boolean'].includes(typeof v)&&v!==null||typeof v==='string'&&v.length>4000))throw new Error('The receipt contains unsupported values.');
 return {schema:SCHEMA,capturedAt:value.capturedAt,values:Object.fromEntries(entries)};
}
export function receiptJSON(receipt,includeNetwork=false) {
 const clean=validateReceipt(receipt);
 if(!includeNetwork)for(const k of Object.keys(clean.values))if(k.startsWith('Connection ·')||k.startsWith('DNS ·'))delete clean.values[k];
 return JSON.stringify(clean,null,2);
}
export function normalizeConnection(body) {
 const data=body?.data;
 if(!data||typeof data!=='object'||typeof data.ip!=='string'||data.ip.length>80||!/^[0-9a-f:.]+$/i.test(data.ip))throw new Error('The connection endpoint did not return a valid address.');
 const fields={ip:'Public IP',asn:'ASN',organization:'Network organization',country:'Country code',colo:'Cloudflare edge',http:'HTTP version',tls:'TLS version'};
 return Object.fromEntries(Object.entries(fields).map(([f,label])=>['Connection · '+label,typeof data[f]==='string'||typeof data[f]==='number'?String(data[f]).slice(0,300):null]));
}
export function observerURL(value) {
 let url;try{url=new URL(value);}catch{throw new Error('Enter the HTTPS URL of your DNS observer.');}
 if(url.protocol!=='https:'||url.username||url.password||url.search||url.hash||url.pathname!=='/')throw new Error('Use an HTTPS origin only, without a path, credentials or query.');
 return url.origin;
}
