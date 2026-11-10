import { useEffect, useMemo, useState } from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import api from './api'

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [me, setMe] = useState(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [register, setRegister] = useState(false)
  const [adminMode, setAdminMode] = useState(false)
  const [tasks, setTasks] = useState([])
  const [routines, setRoutines] = useState([])
  const [daily, setDaily] = useState([])
  const [history, setHistory] = useState([])
  const [filter, setFilter] = useState('All')
  const [search, setSearch] = useState('')
  const [newTask, setNewTask] = useState({title:'', description:'', category:'Fitness'})
  const [tab, setTab] = useState('Today')
  const [message, setMessage] = useState('')

  const load = async () => {
    const [profile, catalogue, routineList, today, past] = await Promise.all([
      api.get('/api/auth/me'), api.get('/api/tasks'), api.get('/api/routines'),
      api.get('/api/daily'), api.get('/api/history?days=30')
    ])
    setMe(profile.data); setTasks(catalogue.data); setRoutines(routineList.data)
    setDaily(today.data); setHistory(past.data)
  }
  useEffect(() => { if (token) load().catch(() => logout()) }, [token])
  const logout = () => { localStorage.removeItem('token'); setToken(null); setMe(null) }
  const signIn = async e => {
    e.preventDefault(); setMessage('')
    try {
      if (register && !adminMode) await api.post('/api/auth/register', {name,email,password})
      const response = await api.post('/api/auth/login', {email,password})
      if (adminMode && response.data.role !== 'admin') { setMessage('This account does not have admin access. Use customer login.'); return }
      localStorage.setItem('token', response.data.access_token); setToken(response.data.access_token)
      setTab(response.data.role === 'admin' ? 'Admin Tasks' : 'Today')
    } catch (err) { setMessage(err.response?.data?.detail || 'Unable to sign in') }
  }
  const addRoutine = async task_id => { await api.post('/api/routines', {task_id}); await load() }
  const toggle = async entry => { await api.patch(`/api/daily/${entry.id}`, {is_completed: !entry.is_completed}); await load() }
  const createTask = async e => {
    e.preventDefault()
    try { await api.post('/api/admin/tasks', newTask); setNewTask({title:'',description:'',category:'Fitness'}); await load(); setMessage('Task created') }
    catch(err) { setMessage(err.response?.data?.detail || 'Could not create task') }
  }
  const categories = ['All', ...new Set(tasks.map(t => t.category))]
  const filtered = tasks.filter(t => (filter === 'All' || t.category === filter) && t.title.toLowerCase().includes(search.toLowerCase()))
  const routineTaskIds = new Set(routines.map(r => r.task_id))
  const done = daily.filter(x => x.is_completed).length
  const pct = daily.length ? Math.round(done * 100 / daily.length) : 0
  const chartData = [{name:'Completed',value:done},{name:'Remaining',value:Math.max(daily.length-done,0)}]
  if (!token) return <main className="auth"><form className="panel authbox" onSubmit={signIn}>
    <div className="logo">✓</div><h1>{adminMode ? 'Admin Login' : 'Todo Application'}</h1><p>{adminMode ? 'Sign in with your administrator account to manage tasks.' : 'Build better habits, one day at a time.'}</p>
    {register && !adminMode && <input placeholder="Full name" value={name} onChange={e=>setName(e.target.value)} required />}
    <input type="email" placeholder="Email address" value={email} onChange={e=>setEmail(e.target.value)} required />
    <input type="password" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} required minLength="8" />
    {message && <div className="notice">{message}</div>}
    <button>{adminMode ? 'Login as admin' : register ? 'Create customer account' : 'Login'}</button>
    {!adminMode && <a onClick={()=>setRegister(!register)}>{register ? 'Already registered? Login' : 'New customer? Create account'}</a>}
    <a onClick={()=>{setAdminMode(!adminMode); setRegister(false); setMessage('')}}>{adminMode ? '← Back to customer login' : 'Admin login'}</a>
  </form></main>
  return <div className="layout">
    <aside><div className="brand">✓ Todo</div><div className="user">Welcome, {me?.name}<small>{me?.role}</small></div>
      {['Today','My Routine','History', ...(me?.role==='admin'?['Admin Tasks','Customers']:[])].map(x=><button className={tab===x?'nav active':'nav'} onClick={()=>setTab(x)} key={x}>{x}</button>)}
      <button className="nav logout" onClick={logout}>Logout</button>
    </aside>
    <main className="content">
      <header><div><h1>{tab}</h1><p>{new Date().toLocaleDateString(undefined,{weekday:'long',year:'numeric',month:'long',day:'numeric'})}</p></div><span className="avatar">{me?.name?.[0]}</span></header>
      {message && <div className="notice">{message}</div>}
      {tab==='Today' && <><section className="stats"><div className="panel"><small>Today's progress</small><strong>{pct}%</strong><span>{done} of {daily.length} tasks completed</span></div><div className="panel"><small>Active routine tasks</small><strong>{routines.length}</strong><span>Your selected daily habits</span></div></section>
        <section className="panel"><h2>Today's tasks</h2>{daily.length===0?<p>No tasks yet. Add tasks from My Routine.</p>:daily.map(x=><label className="taskrow" key={x.id}><input type="checkbox" checked={x.is_completed} onChange={()=>toggle(x)}/><span className={x.is_completed?'completed':''}><b>{x.title}</b><small>{x.category}</small></span></label>)}</section></>}
      {tab==='My Routine' && <><section className="panel"><h2>Task catalogue</h2><div className="filters"><input placeholder="Search tasks..." value={search} onChange={e=>setSearch(e.target.value)}/><select value={filter} onChange={e=>setFilter(e.target.value)}>{categories.map(c=><option key={c}>{c}</option>)}</select></div>
        {filtered.map(t=><div className="catalogue" key={t.id}><div><b>{t.title}</b><small>{t.category} · {t.description}</small></div>{routineTaskIds.has(t.id)?<span className="added">Added</span>:<button className="smallbtn" onClick={()=>addRoutine(t.id)}>Add to routine</button>}</div>)}</section>
        <section className="panel"><h2>My selected routine</h2>{routines.map(r=><div className="catalogue" key={r.id}><div><b>{r.task.title}</b><small>{r.task.category}</small></div><button className="remove" onClick={async()=>{await api.delete(`/api/routines/${r.id}`);await load()}}>Remove</button></div>)}</section></>}
      {tab==='History' && <><section className="panel chartpanel"><div><h2>Last 30 days</h2><p>Daily completion percentage</p><div className="chart"><ResponsiveContainer width="100%" height={210}><PieChart><Pie data={chartData} dataKey="value" innerRadius={60} outerRadius={85} paddingAngle={3}>{chartData.map((x,i)=><Cell key={i} fill={i===0?'#4f46e5':'#e5e7eb'}/>)}</Pie><Tooltip/></PieChart></ResponsiveContainer><b>{pct}%<small>Today</small></b></div></div></section>
        <section className="panel"><h2>Daily history</h2><div className="history">{history.map(d=><div className="historyrow" key={d.date}><span>{new Date(d.date+'T00:00:00').toLocaleDateString(undefined,{month:'short',day:'numeric',weekday:'short'})}</span><div className="bar"><i style={{width:`${d.percentage}%`}}/></div><b>{d.percentage}%</b><small>{d.completed}/{d.total}</small></div>)}</div></section></>}
      {tab==='Admin Tasks' && me?.role==='admin' && <section className="panel"><h2>Create catalogue task</h2><form className="taskform" onSubmit={createTask}><input placeholder="Task title" value={newTask.title} onChange={e=>setNewTask({...newTask,title:e.target.value})} required/><input placeholder="Description" value={newTask.description} onChange={e=>setNewTask({...newTask,description:e.target.value})}/><select value={newTask.category} onChange={e=>setNewTask({...newTask,category:e.target.value})}>{['Fitness','Learning','Health','Personal','General'].map(x=><option>{x}</option>)}</select><button>Create task</button></form>{tasks.map(t=><div className="catalogue" key={t.id}><div><b>{t.title}</b><small>{t.category} · {t.description}</small></div><span className="added">Active</span></div>)}</section>}
      {tab==='Customers' && me?.role==='admin' && <Customers />}
    </main>
  </div>
}
function Customers(){
 const [users,setUsers]=useState([]),[selected,setSelected]=useState(null),[history,setHistory]=useState([])
 useEffect(()=>{api.get('/api/admin/users').then(r=>setUsers(r.data))},[])
 const show=async u=>{setSelected(u);const r=await api.get(`/api/admin/users/${u.id}/history`);setHistory(r.data)}
 return <section className="panel"><h2>Customer accounts</h2>{users.map(u=><div className="catalogue" key={u.id}><div><b>{u.name}</b><small>{u.email}</small></div><button className="smallbtn" onClick={()=>show(u)}>View history</button></div>)}{selected&&<><h3>{selected.name} — last 30 days</h3>{history.map(d=><div className="historyrow" key={d.date}><span>{d.date}</span><div className="bar"><i style={{width:`${d.percentage}%`}}/></div><b>{d.percentage}%</b></div>)}</>}</section>
}
