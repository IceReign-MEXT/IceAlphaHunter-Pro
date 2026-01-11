import React, { useState, useEffect } from 'react';
import { initializeApp } from 'firebase/app';
import { getFirestore, doc, setDoc } from 'firebase/firestore';
import { Shield, Zap, Activity, Crosshair, Cpu, Globe } from 'lucide-react';

const firebaseConfig = JSON.parse(import.meta.env.VITE_FIREBASE_CONFIG || "{}");
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const appId = "mex-war-system";

export default function App() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ telegramId: '', wallet: '', chain: 'SOL' });
  const [auditLog, setAuditLog] = useState([]);

  useEffect(() => {
    const events = [
      { msg: "RUG_DETECTED: \$PEPE_SCAM (LP Removed)", type: "ERR" },
      { msg: "SNIPE_SUCCESS: +2.4 ETH on \$ALPHA", type: "OK" },
      { msg: "REVENUE_ROUTED: 0.012 ETH to Vault", type: "SYS" },
      { msg: "NEW_NODE_ACTIVE: User_8829... Enabled", type: "OK" }
    ];
    const interval = setInterval(() => {
      const entry = events[Math.floor(Math.random() * events.length)];
      setAuditLog(prev => [{ ...entry, id: Math.random(), time: new Date().toLocaleTimeString() }, ...prev.slice(0, 5)]);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleActivate = async () => {
    if (!form.telegramId || !form.wallet) return;
    setLoading(true);
    try {
      const userRef = doc(db, 'artifacts', appId, 'public', 'data', 'verified_users', form.telegramId);
      await setDoc(userRef, { ...form, status: 'WAR_READY', tax: '1.0%', active: true, timestamp: new Date().toISOString() });
      setStep(3);
    } catch (error) { console.error(error); } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-[#020202] text-[#00f2ff] font-mono p-6">
      <nav className="flex justify-between items-center border-b border-[#00f2ff]/10 pb-6">
        <div className="flex items-center gap-3"><Cpu className="animate-pulse" /> <span className="font-black italic">ICE_ALPHA_PRO</span></div>
        <span className="text-[10px] text-green-500 animate-pulse">VAULT_ACTIVE</span>
      </nav>
      <main className="max-w-4xl mx-auto mt-20">
        <div className="bg-zinc-950 border border-[#00f2ff]/30 p-10 rounded-3xl shadow-2xl">
          {step === 3 ? (
             <div className="text-center py-10"><Zap className="mx-auto w-12 h-12 mb-4" /><h2 className="text-2xl font-black italic">NODE_LIVE</h2><p className="opacity-50 mt-2">Return to Telegram to start sniping.</p></div>
          ) : (
            <div className="space-y-6">
              <h2 className="text-2xl font-black italic uppercase">Establish_Link</h2>
              <input placeholder="Telegram User ID" className="w-full bg-black border border-white/10 p-4 rounded-xl" onChange={e => setForm({...form, telegramId: e.target.value})} />
              <input placeholder="Payout Wallet Address" className="w-full bg-black border border-white/10 p-4 rounded-xl" onChange={e => setForm({...form, wallet: e.target.value})} />
              <button onClick={handleActivate} className="w-full bg-[#00f2ff] text-black font-black py-4 rounded-xl italic hover:scale-105 transition-all">
                {loading ? "LINKING..." : "ACTIVATE_WAR_SYSTEM (0.5 SOL)"}
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
