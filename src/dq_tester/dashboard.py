import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import ast
import argparse
import sys
from pathlib import Path

# Import your existing loaders module
try:
    from dq_tester.loaders import get_connections
except ImportError:
    st.error("Could not import dq_tester.loaders. Please ensure dq_tester package is installed or in your PYTHONPATH.")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Data Quality Dashboard",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

def find_connections_file(provided_path=None):
    """Find connections.yaml file in default locations or use provided path"""
    if provided_path:
        path = Path(provided_path).expanduser()
        if path.exists():
            return str(path)
        else:
            st.error(f"Provided connections file not found: {provided_path}")
            st.stop()
    
    # Check default locations in order
    default_locations = [
        'connections.yaml',  # Current directory
        '~/.dq_tester/connections.yaml',  # User home directory
        '/etc/dq_tester/connections.yaml',  # System-wide (Linux)
    ]
    
    for location in default_locations:
        path = Path(location).expanduser()
        if path.exists():
            return str(path)
    
    st.error(f"connections.yaml not found in any default location: {', '.join(default_locations)}")
    st.stop()

@st.cache_resource
def get_duckdb_connection(connections_file=None):
    """Get DuckDB connection from connections.yaml via loaders.py"""
    try:
        # Set the connections file path if provided
        connections_path = find_connections_file(connections_file)
        
        connections = get_connections(connections_path)
        results_conn = connections.get_connection("results_db")
        
        if results_conn is None:
            st.error("'results_db' connection not found in connections.yaml")
            st.stop()
        
        if results_conn.driver != "DuckDB":
            st.error(f"'results_db' is not a DuckDB connection (found: {results_conn.driver})")
            st.stop()
        
        # Connect to DuckDB
        conn = duckdb.connect(results_conn.database, read_only=True)
        return conn
    except Exception as e:
        st.error(f"Error connecting to DuckDB: {str(e)}")
        st.stop()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data(_conn):
    """Load test results from DuckDB"""
    query = """
    SELECT 
        connection_name,
        tested_object,
        test_ts,
        dq_test_name,
        status,
        test_parameters,
        threshold_op,
        threshold_val,
        test_sql,
        error
    FROM test_results
    ORDER BY test_ts DESC
    """
    df = _conn.execute(query).fetchdf()
    
    # Parse test_parameters JSON
    def parse_column_name(params):
        if pd.isna(params) or params == '' or params is None:
            return None
        try:
            parsed = ast.literal_eval(params) if isinstance(params, str) else params
            return parsed.get('column_name', None)
        except:
            return None
    
    df['column_name'] = df['test_parameters'].apply(parse_column_name)
    
    return df

def calculate_metrics(df):
    """Calculate key metrics"""
    total_tests = len(df)
    passed_tests = len(df[df['status'] == 'PASS'])
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    # Tests in last 24 hours
    if len(df) > 0:
        last_24h = datetime.now() - timedelta(hours=24)
        recent_df = df[pd.to_datetime(df['test_ts']) >= last_24h]
        failed_24h = len(recent_df[recent_df['status'] == 'FAIL'])
    else:
        failed_24h = 0
    
    # Unique columns tested
    columns_tested = df['column_name'].dropna().nunique()
    
    return {
        'total_tests': total_tests,
        'pass_rate': pass_rate,
        'failed_24h': failed_24h,
        'columns_tested': columns_tested
    }

def plot_status_distribution(df):
    """Create status distribution donut chart"""
    status_counts = df['status'].value_counts()
    
    # Define distinct colors for each status
    colors = {
        'PASS': '#10b981',    # Green
        'FAIL': '#ef4444',    # Red
        'ERROR': '#f59e0b'    # Orange/Yellow
    }
    
    color_map = [colors.get(status, '#6b7280') for status in status_counts.index]
    
    fig = go.Figure(data=[go.Pie(
        labels=status_counts.index,
        values=status_counts.values,
        hole=0.4,
        marker=dict(colors=color_map)
    )])
    
    fig.update_layout(
        title="Test Status Distribution",
        height=350,
        showlegend=True
    )
    
    return fig

def plot_trends_over_time(df):
    """Create time series of test results"""
    df_time = df.copy()
    df_time['test_date'] = pd.to_datetime(df_time['test_ts']).dt.date
    
    trend_data = df_time.groupby(['test_date', 'status']).size().reset_index(name='count')
    
    fig = px.line(
        trend_data,
        x='test_date',
        y='count',
        color='status',
        title='Test Trends Over Time',
        labels={'test_date': 'Date', 'count': 'Number of Tests'},
        color_discrete_map={
            'PASS': '#10b981',
            'FAIL': '#ef4444',
            'ERROR': '#f59e0b'
        }
    )
    
    fig.update_layout(height=350, hovermode='x unified')
    
    return fig

def plot_connection_health(df):
    """Create stacked bar chart by connection"""
    conn_status = df.groupby(['connection_name', 'status']).size().reset_index(name='count')
    
    fig = px.bar(
        conn_status,
        x='connection_name',
        y='count',
        color='status',
        title='Test Results by Connection',
        labels={'connection_name': 'Connection', 'count': 'Number of Tests'},
        color_discrete_map={
            'PASS': '#10b981',
            'FAIL': '#ef4444',
            'ERROR': '#f59e0b'
        }
    )
    
    fig.update_layout(height=350, barmode='stack')
    
    return fig

def plot_column_health(df):
    """Create column-level health analysis"""
    col_df = df[df['column_name'].notna()].copy()
    
    if len(col_df) == 0:
        return None
    
    col_stats = col_df.groupby('column_name').agg({
        'status': ['count', lambda x: (x == 'FAIL').sum()]
    }).reset_index()
    
    col_stats.columns = ['column_name', 'total_tests', 'failed_tests']
    col_stats['pass_rate'] = ((col_stats['total_tests'] - col_stats['failed_tests']) / col_stats['total_tests'] * 100)
    col_stats = col_stats.sort_values('failed_tests', ascending=False).head(15)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=col_stats['column_name'],
        y=col_stats['failed_tests'],
        name='Failed',
        marker_color='#ef4444'
    ))
    
    fig.add_trace(go.Bar(
        x=col_stats['column_name'],
        y=col_stats['total_tests'] - col_stats['failed_tests'],
        name='Passed',
        marker_color='#10b981'
    ))
    
    fig.update_layout(
        title='Column-Level Test Results (Top 15)',
        xaxis_title='Column Name',
        yaxis_title='Number of Tests',
        barmode='stack',
        height=400,
        xaxis_tickangle=-45
    )
    
    return fig

def plot_object_health(df):
    """Create tested object health analysis"""
    obj_status = df.groupby(['tested_object', 'status']).size().reset_index(name='count')
    
    # Get top 15 objects by total test count
    top_objects = df['tested_object'].value_counts().head(15).index
    obj_status = obj_status[obj_status['tested_object'].isin(top_objects)]
    
    fig = px.bar(
        obj_status,
        x='tested_object',
        y='count',
        color='status',
        title='Test Results by Object (Top 15)',
        labels={'tested_object': 'Tested Object', 'count': 'Number of Tests'},
        color_discrete_map={
            'PASS': '#10b981',
            'FAIL': '#ef4444',
            'ERROR': '#f59e0b'
        }
    )
    
    fig.update_layout(height=400, barmode='stack', xaxis_tickangle=-45)
    
    return fig

def main():
    st.title("📊 Data Quality Dashboard")
    st.markdown("Real-time monitoring of data quality test results")
    
    # Check for command line argument for connections file
    connections_file = None
    if len(sys.argv) > 1:
        connections_file = sys.argv[1]
    
    # Get DuckDB connection
    conn = get_duckdb_connection(connections_file)
    
    # Load data
    with st.spinner("Loading test results..."):
        df = load_data(conn)
    
    if len(df) == 0:
        st.warning("No test results found in the database.")
        return
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Date range filter
    min_date = pd.to_datetime(df['test_ts']).min().date()
    max_date = pd.to_datetime(df['test_ts']).max().date()
    
    # Calculate default start date (7 days ago or min_date, whichever is later)
    default_start = max(min_date, max_date - timedelta(days=7))
    
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(default_start, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Connection filter
    connections = sorted([c for c in df['connection_name'].unique() if c is not None and pd.notna(c)])
    selected_connection = st.sidebar.multiselect(
        "Connection",
        connections,
        default=[],
        placeholder="All connections"
    )
    
    # Filter data for dependent dropdowns
    filtered_for_objects = df.copy()
    if len(selected_connection) > 0:
        filtered_for_objects = filtered_for_objects[filtered_for_objects['connection_name'].isin(selected_connection)]
    
    # Tested Object filter (filtered by connection)
    tested_objects = sorted([o for o in filtered_for_objects['tested_object'].unique() if o is not None and pd.notna(o)])
    selected_object = st.sidebar.multiselect(
        "Tested Object",
        tested_objects,
        default=[],
        placeholder="All objects"
    )
    
    # Filter data for column names based on connection and object
    filtered_for_columns = filtered_for_objects.copy()
    if len(selected_object) > 0:
        filtered_for_columns = filtered_for_columns[filtered_for_columns['tested_object'].isin(selected_object)]
    
    # Column name filter (filtered by connection and tested object)
    column_names = sorted([c for c in filtered_for_columns['column_name'].dropna().unique() if c is not None])
    selected_column = st.sidebar.multiselect(
        "Column Name",
        column_names,
        default=[],
        placeholder="All columns"
    )
    
    # Apply filters
    filtered_df = df.copy()
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (pd.to_datetime(filtered_df['test_ts']).dt.date >= start_date) &
            (pd.to_datetime(filtered_df['test_ts']).dt.date <= end_date)
        ]
    
    if len(selected_connection) > 0:
        filtered_df = filtered_df[filtered_df['connection_name'].isin(selected_connection)]
    
    if len(selected_object) > 0:
        filtered_df = filtered_df[filtered_df['tested_object'].isin(selected_object)]
    
    if len(selected_column) > 0:
        filtered_df = filtered_df[filtered_df['column_name'].isin(selected_column)]
    
    # Calculate metrics
    metrics = calculate_metrics(filtered_df)
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Tests", f"{metrics['total_tests']:,}")
    
    with col2:
        st.metric("Pass Rate", f"{metrics['pass_rate']:.1f}%")
    
    with col3:
        st.metric("Failed (24h)", metrics['failed_24h'])
    
    with col4:
        st.metric("Columns Tested", metrics['columns_tested'])
    
    st.divider()
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = plot_status_distribution(filtered_df)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        fig2 = plot_connection_health(filtered_df)
        st.plotly_chart(fig2, use_container_width=True)
    
    # Trends over time
    fig3 = plot_trends_over_time(filtered_df)
    st.plotly_chart(fig3, use_container_width=True)
    
    # Object and Column health
    col1, col2 = st.columns(2)
    
    with col1:
        fig4 = plot_object_health(filtered_df)
        st.plotly_chart(fig4, use_container_width=True)
    
    with col2:
        fig5 = plot_column_health(filtered_df)
        if fig5:
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("No column-level test data available")
    
    st.divider()
    
    # Detailed results table
    st.subheader("📋 Detailed Test Results")
    
    # Format the display dataframe
    display_df = filtered_df[[
        'test_ts', 'connection_name', 'tested_object', 
        'dq_test_name', 'status', 'column_name', 'error'
    ]].copy()
    
    display_df['test_ts'] = pd.to_datetime(display_df['test_ts']).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Color code status
    def color_status(val):
        colors = {
            'PASS': 'background-color: #d1fae5',
            'FAIL': 'background-color: #fee2e2',
            'ERROR': 'background-color: #fef3c7'
        }
        return colors.get(val, '')
    
    styled_df = display_df.style.map(color_status, subset=['status'])
    
    st.dataframe(styled_df, width="stretch", height=400)
    
    # Download button
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Results as CSV",
        data=csv,
        file_name=f"dq_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    # Footer
    st.divider()
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total records: {len(df):,}")

def run_dashboard():
    """Entry point for the dashboard CLI command"""
    import sys
    import argparse
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='Run the DQ Tester Dashboard')
    parser.add_argument('connections_file', nargs='?', help='Path to connections.yaml file')
    parser.add_argument('--port', type=int, default=8501, help='Port to run the dashboard on (default: 8501)')
    
    args = parser.parse_args()
    
    # Build streamlit command
    streamlit_args = ['streamlit', 'run', __file__, '--server.port', str(args.port)]
    
    if args.connections_file:
        streamlit_args.append(args.connections_file)
    
    sys.argv = streamlit_args
    
    # Run streamlit
    from streamlit.web import cli as stcli
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
