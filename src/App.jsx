import React, { useState } from 'react';
import { initializeApp } from 'firebase/app';
import { getFirestore, doc, setDoc } from 'firebase/firestore';
import { Shield, Zap, Activity, Cpu, Lock } from 'lucide-react';

const firebaseConfig = JSON.parse(import.meta.env.VITE_FIREBASE_CONFIG || "{}");
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

export default function App() {
  const [form, setForm] = useState({ id: '', wallet: '' });
  const [done, setDone] = useState(false);

  const activate = async () => {
    await setDoc(doc(db, 'artifacts', 'mex-war-system', 'public', 'data', 'verified_users', form.id), {
      ...form, status: 'WAR_READY', tax: '1%', date: new Date().toISOString()
    });
    setDone(true);
  };

  return (
    <div className="min-h-screen bg-black text-[#00f2ff] font-mono p-10">
      <div className="max-w-md mx-auto bg-zinc-950 border-2 border-[#00f2ff] p-8 rounded-[2rem]">
        <Cpu className="w-12 h-12 mb-4 animate-pulse" />
        <h1 className="text-2xl font-black italic mb-6">ACTIVATE_NODE</h1>
        {done ? <div className="text-green-500 font-bold">PROTOCOL_SYNCED</div> : (
          <div className="space-y-4">
            <input className="w-full bg-black border border-white/20 p-4 rounded-xl" placeholder="TELEGRAM_ID" onChange={e=>setForm({...form, id: e.target.value})} />
            <input className="w-full bg-black border border-white/20 p-4 rounded-xl" placeholder="WALLET" onChange={e=>setForm({...form, wallet: e.target.value})} />
            <button onClick={activate} className="w-full bg-[#00f2ff] text-black font-black py-4 rounded-xl">ACTIVATE (0.5 SOL)</button>
          </div>
        )}
      </div>
    </div>
  );
}

