from common.core.base_agent import BaseAgent
import zmq
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
import streamlit as st
import pandas as pd
import plotly.express as px
from common.env_helpers import get_env

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('timeline_ui.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TimelineUIServer(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Timelineuiserver")
        """Initialize the TimelineUIServer with ZMQ sockets."""
        self.context = zmq.Context()
        
        # REQ socket for EpisodicMemoryAgent
        self.memory_socket = self.context.socket(zmq.REQ)
        self.memory_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.memory_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.memory_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5629")  # EpisodicMemoryAgent
        
        # REQ socket for MetaCognitionAgent
        self.meta_socket = self.context.socket(zmq.REQ)
        self.meta_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.meta_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.meta_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5630")  # MetaCognitionAgent
        
        logger.info("TimelineUIServer initialized")
    
    def _get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history from EpisodicMemoryAgent."""
        try:
            self.memory_socket.send_json({
                'action': 'get_conversation_history'
            })
            
            response = self.memory_socket.recv_json()
            
            if response['status'] == 'success':
                return response['history']
            else:
                logger.error(f"Failed to get conversation history: {response.get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []
    
    def _get_thought_process(self) -> List[Dict[str, Any]]:
        """Get AI thought process from MetaCognitionAgent."""
        try:
            self.meta_socket.send_json({
                'action': 'get_thought_process'
            })
            
            response = self.meta_socket.recv_json()
            
            if response['status'] == 'success':
                return response['thoughts']
            else:
                logger.error(f"Failed to get thought process: {response.get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting thought process: {str(e)}")
            return []
    
    def _create_timeline_data(self) -> pd.DataFrame:
        """Create a combined timeline of conversations and thoughts."""
        conversations = self._get_conversation_history()
        thoughts = self._get_thought_process()
        
        # Convert to DataFrame
        data = []
        
        # Add conversations
        for conv in conversations:
            data.append({
                'timestamp': datetime.fromisoformat(conv['timestamp']),
                'type': 'conversation',
                'content': conv['content'],
                'speaker': conv['speaker']
            })
        
        # Add thoughts
        for thought in thoughts:
            data.append({
                'timestamp': datetime.fromisoformat(thought['timestamp']),
                'type': 'thought',
                'content': thought['content'],
                'speaker': 'AI'
            })
        
        # Create DataFrame and sort by timestamp
        df = pd.DataFrame(data)
        df = df.sort_values('timestamp')
        
        return df
    
    def run(self):
        """Run the Streamlit web interface."""
        st.set_page_config(
            page_title="AI Assistant Timeline",
            page_icon="🤖",
            layout="wide"
        )
        
        st.title("AI Assistant Timeline")
        
        # Add refresh button
        if st.button("Refresh Timeline"):
            st.experimental_rerun()
        
        # Get timeline data
        df = self._create_timeline_data()
        
        if df.empty:
            st.info("No timeline data available yet.")
            return
        
        # Create timeline visualization
        fig = px.timeline(
            df,
            x_start='timestamp',
            y='type',
            color='speaker',
            hover_data=['content'],
            title="Conversation and Thought Timeline"
        )
        
        fig.update_layout(
            height=600,
            showlegend=True,
            legend_title="Speaker",
            xaxis_title="Time",
            yaxis_title="Type"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display detailed view
        st.subheader("Detailed Timeline")
        
        for _, row in df.iterrows():
            with st.expander(f"{row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {row['type'].title()} by {row['speaker']}"):
                st.write(row['content'])
    
    def stop(self):
        """Stop the server and clean up resources."""
        self.memory_socket.close()
        self.meta_socket.close()
        self.context.term()

if __name__ == '__main__':
    server = TimelineUIServer()
    try:
        server.run()
    except KeyboardInterrupt:
        server.stop() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise