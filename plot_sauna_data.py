import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('/Users/baranekm/Documents/Python/sauna-attendance/data/sauna_data_20241123.csv')
df = df[df['session_type'] != 'closed']
# Plot persons_count and temperature_sauna over time
plt.figure(figsize=(10, 6))

# Plot persons_count
plt.plot(df['timestamp'], df['persons_sauna'], label='Persons Count', marker='o')

# Plot temperature_sauna
plt.plot(df['timestamp'], df['temperature_home'], label='Temperature', marker='s')

# Formatting the plot
plt.title('Persons Count and Temperature Over Time')
# Decrease number of x-ticks
plt.xticks(df['timestamp'][::6], rotation=45)  # Select every second timestamp
plt.xlabel('Timestamp')
plt.ylabel('Number of Persons')
plt.legend()
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()

# Show the plot
plt.show()
