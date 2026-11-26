import test from 'node:test';
import assert from 'node:assert/strict';
import {SCHEMA,compareReceipts,validateReceipt,receiptJSON,normalizeConnection,observerURL} from '../web/model.mjs';
const receipt=values=>({schema:SCHEMA,capturedAt:'2026-11-26T00:00:00Z',values});
test('comparison distinguishes absent, false and changed fields without timestamp noise',()=>{assert.deepEqual(compareReceipts(receipt({a:false,b:1}),receipt({a:false,b:2,c:null})).map(x=>x.key),['b','c']);});
test('exports strip network fields by default without mutating captured receipt',()=>{const r=receipt({'Connection · Public IP':'192.0.2.2','DNS · Observed resolver addresses':'192.0.2.3',local:'test'});assert.deepEqual(JSON.parse(receiptJSON(r)).values,{local:'test'});assert.equal(Object.keys(r.values).length,3);assert.equal(Object.keys(JSON.parse(receiptJSON(r,true)).values).length,3);});
test('reject unsupported import structure, objects and oversized strings',()=>{for(const r of [{},receipt([]),receipt({value:{secret:true}}),receipt({a:'a'.repeat(4001)})])assert.throws(()=>validateReceipt(r));});
test('connection schema is bounded and accepts IPv6',()=>{const r=normalizeConnection({data:{ip:'2001:db8::1',asn:64500,organization:'Example',extra:'ignore'}});assert.equal(r['Connection · Public IP'],'2001:db8::1');assert.equal(r['Connection · ASN'],'64500');assert.throws(()=>normalizeConnection({data:{ip:'<script>'}}));});
test('optional observer accepts HTTPS origins only',()=>{assert.equal(observerURL('https://observer.example/'),'https://observer.example');for(const url of ['http://example.com','https://user:secret@example.com','https://example.com/path','https://example.com/?token=x','javascript:alert(1)'])assert.throws(()=>observerURL(url));});
