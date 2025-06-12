import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def create_daily_usage_density(history_data):
    """
    Creates an overlapping density plot showing server usage patterns by day of week.
    
    Args:
        history_data: List of dicts containing play history with timestamps
        
    Returns:
        str: Path to saved plot image
    """
    # Convert history data to DataFrame
    df = pd.DataFrame(history_data)
    
    if df.empty:
        # Create empty plot if no data
        plt.figure(figsize=(12, 8))
        plt.text(0.5, 0.5, 'No usage data available', ha='center', va='center', transform=plt.gca().transAxes)
        plot_path = 'assets/images/daily_usage_density.png'
        plt.savefig(plot_path, bbox_inches='tight', dpi=300)
        plt.close()
        return plot_path
    
    # Convert timestamp to datetime and extract hour and day
    # Make sure we're handling the timestamp correctly
    if 'date' in df.columns:
        # 'date' field contains Unix timestamps
        df['datetime'] = pd.to_datetime(df['date'], unit='s')
    else:
        print("Warning: No 'date' field found in history data")
        return None
    
    df['hour'] = df['datetime'].dt.hour
    df['day'] = df['datetime'].dt.day_name()
    
    # Debug: Print some sample data to verify hour extraction
    print(f"Sample data verification:")
    print(f"Total records: {len(df)}")
    if len(df) > 0:
        sample = df.head(3)[['datetime', 'hour', 'day']]
        print(sample)
        print(f"Hour range: {df['hour'].min()} to {df['hour'].max()}")
    
    # Set up the day order (Sunday to Saturday)
    day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    # Filter to only include days that have data
    df = df[df['day'].isin(day_order)]
    
    if df.empty:
        # Create empty plot if no data after filtering
        plt.figure(figsize=(12, 8))
        plt.text(0.5, 0.5, 'No usage data available', ha='center', va='center', transform=plt.gca().transAxes)
        plot_path = 'assets/images/daily_usage_density.png'
        plt.savefig(plot_path, bbox_inches='tight', dpi=300)
        plt.close()
        return plot_path
    
    # Set the theme for clean background matching light grey content card
    sns.set_theme(style="white")
    
    # Use the user-provided custom color palette
    pal = ["#7e55a3", "#6368b6", "#4079bf", "#0087bf", "#0093b7", "#009daa", "#26a69a"]

    # --- Shift hours for 6am to 6am view ---
    # 6am becomes 0, 5am becomes 23
    df['shifted_hour'] = (df['hour'] - 6 + 24) % 24

    # Initialize the FacetGrid object
    g = sns.FacetGrid(df, row="day", hue="day", aspect=15, height=.75, 
                      palette=pal, row_order=day_order)
    
    # Draw the densities in a few steps
    g.map(sns.kdeplot, "shifted_hour",
          bw_adjust=.5, clip_on=False,
          fill=True, alpha=1, linewidth=1.5)
    g.map(sns.kdeplot, "shifted_hour", clip_on=False, color="w", lw=2, bw_adjust=.5)
    
    # Add a reference line at y=0 using the hue mapping
    g.refline(y=0, linewidth=2, linestyle="-", color=None, clip_on=False)
    
    # Define and use a simple function to label the plot in axes coordinates
    def label(x, color, label):
        ax = plt.gca()
        # Position the day label on the left side, vertically centered
        ax.text(-0.02, .5, label, fontweight="bold", color=color,
                ha="right", va="center", transform=ax.transAxes, fontsize=12)
    
    g.map(label, "hour")
    
    # Set the subplots to overlap
    g.figure.subplots_adjust(hspace=-.25)
    
    # Remove axes details that don't play well with overlap
    g.set_titles("")
    g.set(yticks=[], ylabel="")
    g.despine(bottom=True, left=True)

    # --- Make subplot backgrounds transparent and set new axis ---
    for i, ax in enumerate(g.axes.flat):
        # Remove the background patch
        ax.patch.set_visible(False)

        # Set the x-axis limits from 0 to 24 (for our shifted hours)
        ax.set_xlim(0, 24)

        # Only add x-axis labels to the bottom-most plot
        if i == len(g.axes.flat) - 1:
            # Create tick positions every 4 hours on the 0-24 scale
            tick_positions = list(range(0, 25, 4))
            
            # Map tick positions back to original hours (6am to 6am)
            original_hours = [(pos + 6) % 24 for pos in tick_positions]
            
            time_labels = []
            for hour in original_hours:
                if hour == 0:
                    time_labels.append("12am")
                elif hour == 6:
                    time_labels.append("6am")
                elif hour < 12:
                    time_labels.append(f"{hour}am")
                elif hour == 12:
                    time_labels.append("12pm")
                else:
                    time_labels.append(f"{hour-12}pm")
            
            # The last label should be "6am" again
            time_labels[-1] = "6am"
            
            ax.set_xticks(tick_positions)
            ax.set_xticklabels(time_labels, rotation=0, ha='center', fontsize=12)
            ax.tick_params(colors='black')
        else:
            # Remove x-tick labels from all other plots
            ax.set_xticklabels([])

    # Remove titles and labels completely
    g.fig.suptitle("")  # Remove main title
    
    # Save with a transparent background for the figure itself
    plot_path = 'assets/images/daily_usage_density.png'
    plt.savefig(plot_path, bbox_inches='tight', dpi=300, transparent=True)
    plt.close()
    
    # Reset seaborn theme
    sns.reset_defaults()
    
    return plot_path

def create_user_content_scatter(play_data):
    """
    Creates a scatter plot showing user activity across different content types.
    
    Args:
        play_data: List of dicts containing play history with content types and users
        
    Returns:
        str: Path to saved plot image
    """
    if not play_data:
        # Create empty plot if no data
        plt.figure(figsize=(12, 8))
        plt.text(0.5, 0.5, 'No user data available', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('User Activity by Content Type', fontsize=16)
        plot_path = 'assets/images/user_content_scatter.png'
        plt.savefig(plot_path, bbox_inches='tight', dpi=300)
        plt.close()
        return plot_path
    
    # Convert to DataFrame
    df = pd.DataFrame(play_data)
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    # Create scatter plot for each content type
    colors = ['red', 'blue', 'green']
    markers = ['o', 's', '^']
    
    for i, (media_type, label) in enumerate([('episode', 'TV Shows'), ('movie', 'Movies'), ('track', 'Music')]):
        subset = df[df['media_type'] == media_type]
        if not subset.empty:
            plt.scatter(subset['duration'], subset['total_plays'], 
                       c=colors[i % len(colors)], 
                       marker=markers[i % len(markers)],
                       alpha=0.6, 
                       label=label,
                       s=60)
    
    plt.title('User Activity by Content Type', fontsize=16)
    plt.xlabel('Duration (minutes)')
    plt.ylabel('Number of Plays')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Save and return path
    plot_path = 'assets/images/user_content_scatter.png'
    plt.savefig(plot_path, bbox_inches='tight', dpi=300)
    plt.close()
    return plot_path

def create_content_growth_line(library_data):
    """
    Creates a line plot showing growth of different content types over time.
    
    Args:
        library_data: List of dicts containing added dates and content types
        
    Returns:
        str: Path to saved plot image
    """
    if not library_data:
        # Create empty plot if no data
        plt.figure(figsize=(12, 6))
        plt.text(0.5, 0.5, 'No library data available', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('Library Growth Over Time', fontsize=16)
        plot_path = 'assets/images/content_growth_line.png'
        plt.savefig(plot_path, bbox_inches='tight', dpi=300)
        plt.close()
        return plot_path
    
    # Convert to DataFrame
    df = pd.DataFrame(library_data)
    
    # Convert Unix timestamp to datetime
    try:
        df['added_at'] = pd.to_datetime(df['added_at'], unit='s')
    except (ValueError, TypeError):
        # Try parsing as ISO string if Unix timestamp fails
        df['added_at'] = pd.to_datetime(df['added_at'])
    
    # Group by date and content type
    daily_adds = df.groupby([pd.Grouper(key='added_at', freq='D'), 'section_type']).size().unstack(fill_value=0)
    
    # Ensure all desired columns exist, even if there's no data for them
    for col in ['movie', 'season', 'album']:
        if col not in daily_adds.columns:
            daily_adds[col] = 0
            
    # Rename columns for clarity in the legend
    daily_adds = daily_adds.rename(columns={'movie': 'Movies', 'season': 'TV Seasons', 'album': 'Music Albums'})

    # Calculate cumulative sums
    cumulative = daily_adds.cumsum()
    
    # Calculate the total based on the specified columns
    cumulative['Total'] = cumulative[['Movies', 'TV Seasons', 'Music Albums']].sum(axis=1)
    
    # Create the plot
    plt.figure(figsize=(12, 6))
    
    # Plot each content type
    for column in cumulative.columns:
        if column == 'Total':
            plt.plot(cumulative.index, cumulative[column], 
                    label=column, linewidth=3, color='black')
        else:
            plt.plot(cumulative.index, cumulative[column], 
                    label=column, linewidth=2, alpha=0.7)
    
    plt.title('Library Growth Over Time', fontsize=16)
    plt.xlabel('Date')
    plt.ylabel('Number of Items')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Save and return path
    plot_path = 'assets/images/content_growth_line.png'
    plt.savefig(plot_path, bbox_inches='tight', dpi=300)
    plt.close()
    return plot_path 