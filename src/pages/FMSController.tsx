
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FaRegCommentDots, FaWhatsapp, FaTelegramPlane } from "react-icons/fa";


const COLUMN_NAMES = ["NEW", "Pending", "In Progress"];


const REFRESH_INTERVAL = 120; // seconds
const FMSController = () => {
  const [columns, setColumns] = useState({ NEW: [], Pending: [], "In Progress": [] });
  const [loading, setLoading] = useState(false);
  const [taskMessages, setTaskMessages] = useState({});
  const [showNotification, setShowNotification] = useState(false);
  const [notificationMsg, setNotificationMsg] = useState("");
  const [timer, setTimer] = useState(REFRESH_INTERVAL);
  const navigate = useNavigate();

  // Redirect to login if not authenticated
  useEffect(() => {
    const username = localStorage.getItem("username");
    if (!username) {
      navigate("/");
    }
  }, [navigate]);

  useEffect(() => {
    setLoading(true);
    const username = localStorage.getItem("username") || "demo";
    const abortController = new window.AbortController();
    const API_URL = import.meta.env.VITE_API_URL;
    const fetchColumns = async () => {
      try {
        const res = await fetch(`${API_URL}/check_new_tasks?username=${username}`, { signal: abortController.signal });
        const data = await res.json();
        setColumns(data.columns || { NEW: [], Pending: [], "In Progress": [] });
        // After columns, fetch messages for these tasks
        const msgRes = await fetch(`${API_URL}/check_task_messages?username=${username}`, { signal: abortController.signal });
        const msgData = await msgRes.json();
        setTaskMessages(msgData.messages || {});
        // Notification logic: show popup if any task has new message
const newMsgTasks = Object.entries(msgData.messages || {}).filter(([_, v]) => (v as any).has_new_message);        if (newMsgTasks.length > 0) {
          setNotificationMsg(`You have new messages in ${newMsgTasks.length} task(s)!`);
          setShowNotification(true);
          setTimeout(() => setShowNotification(false), 4000);
        }
      } catch {
        setColumns({ NEW: [], Pending: [], "In Progress": [] });
        setTaskMessages({});
      } finally {
        setLoading(false);
      }
    };
    fetchColumns();
    setTimer(REFRESH_INTERVAL);
    const interval = setInterval(() => {
      fetchColumns();
      setTimer(REFRESH_INTERVAL);
    }, REFRESH_INTERVAL * 1000);
    const timerInterval = setInterval(() => {
      setTimer((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => {
      abortController.abort();
      clearInterval(interval);
      clearInterval(timerInterval);
    };
  }, []);

  const handleClick = () => {
    window.open("https://msp.go2field.iq/board/a22c39cb-093c-d83e-7dd1-a8c7a5d0fa7b", "_blank");
  };

  return (
    <div className="h-screen w-screen bg-black flex flex-col items-center justify-start">
      {/* Logout button in top left */}
      <div style={{ position: "fixed", top: 20, left: 32, zIndex: 100 }}>
        <button
          className="bg-red-600 text-white px-4 py-2 rounded shadow-lg text-lg font-bold hover:bg-red-700 transition-colors"
          onClick={() => {
            localStorage.removeItem("username");
            navigate("/");
            window.location.reload(); // Ensures all requests are aborted and state is reset
          }}
        >
          Logout
        </button>
      </div>
      {/* Timer in top right */}
      <div style={{ position: "fixed", top: 20, right: 32, zIndex: 100 }}>
        <div className="bg-gray-900 text-white px-4 py-2 rounded shadow-lg text-lg font-bold">
          Refresh in: {timer}s
        </div>
      </div>
      <div className="w-full flex flex-col items-center mt-16">
        <h1 className="text-5xl font-bold text-white mb-10">FMS Controller</h1>
        {loading ? (
          <div className="flex flex-col items-center justify-center mt-12">
            <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-400 mb-4"></div>
            <div className="text-white text-xl">Scraping tasks, please wait...</div>
          </div>
        ) : (
          <>
            <div
              className={`bg-gray-900 text-white rounded-2xl shadow-2xl p-12 text-left min-w-[400px] min-h-[180px] flex flex-col justify-center items-start transition-all duration-200 cursor-pointer hover:bg-gray-800`}
              onClick={handleClick}
              style={{ opacity: columns.NEW.length > 0 ? 1 : 0.7, fontSize: '2.5rem' }}
            >
              <h2 className="text-4xl font-extrabold mb-4">NEW Tasks = {columns.NEW.length}</h2>
              <p className="text-xl mb-2">{columns.NEW.length > 0 ? "Click to view new tasks!" : "No new tasks."}</p>
            </div>
            {/* Cards for NEW, Pending, In Progress */}
            <div className="flex gap-8 mt-12">
              {COLUMN_NAMES.map((colName) => (
                <div key={colName} className="bg-gray-800 rounded-xl shadow-lg p-6 min-w-[320px]">
                  <h3 className="text-2xl font-bold text-white mb-2">{colName}</h3>
                  <div className="text-lg text-blue-300 mb-4">Tasks: {columns[colName].length}</div>
                  <div className="space-y-4">
                    {columns[colName].length === 0 ? (
                      <div className="text-gray-400">No tasks</div>
                    ) : (
                      columns[colName].map((task, idx) => (
                        <div key={task.CaseNumber + '-' + idx} className="bg-gray-900 rounded-lg p-4 mb-2">
                          <div className="font-mono text-white text-base mb-1">{task.CaseNumber} - {task.Title}</div>
                          <div className="text-sm text-gray-400 mb-2">{task.FBG}</div>
                          <div className="flex flex-col gap-2">
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-300">Messages:</span>
                              <button
                                onClick={() => {
                                  if (task.uuid) {
                                    window.open(`https://msp.go2field.iq/task/${task.uuid}`, "_blank");
                                  }
                                }}
                                style={{ background: "none", border: "none", padding: 0, cursor: "pointer" }}
                                title="View messages"
                              >
                                <FaRegCommentDots
                                  className={
                                    taskMessages[task.CaseNumber]?.has_new_message
                                      ? "text-green-400 animate-bounce"
                                      : "text-gray-500"
                                  }
                                  size={22}
                                />
                              </button>
                            </div>
                            <div className="flex items-center gap-3 mt-2">
                              <FaWhatsapp className="text-green-500" size={22} />
                              <span className="text-xs text-white">WhatsApp Group 1</span>
                              <FaWhatsapp className="text-green-500" size={22} />
                              <span className="text-xs text-white">WhatsApp Group 2</span>
                              <FaWhatsapp className="text-green-500" size={22} />
                              <span className="text-xs text-white">WhatsApp Group 3</span>
                              <FaWhatsapp className="text-green-500" size={22} />
                              <span className="text-xs text-white">WhatsApp Group 4</span>
                              <FaTelegramPlane className="text-blue-400" size={22} />
                              <span className="text-xs text-white">Telegram Group</span>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      {/* Notification popup */}
      {showNotification && (
        <div className="fixed top-8 right-8 bg-blue-600 text-white px-6 py-3 rounded shadow-lg z-50 animate-fade-in">
          <span className="font-bold">🔔</span> {notificationMsg}
        </div>
      )}
      <div className="w-full flex justify-center items-center mt-16 mb-4">
        <span className="text-gray-400 text-lg">Created by Marwan_Al-Ameen</span>
      </div>
    </div>
    </div>
  );

};

export default FMSController;