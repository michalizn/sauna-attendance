import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

df = pd.read_csv(r'/Users/baranekm/Documents/Python/sauna_data_20241117171433.csv')
# Plot persons_count and temperature_sauna over time
plt.figure(figsize=(10, 6))

# Plot persons_count
plt.plot(df['timestamp'], df['persons_count'], label='Persons Count', marker='o')

# Plot temperature_sauna
plt.plot(df['timestamp'], df['temperature_sauna'], label='Temperature Sauna', marker='s')

# Formatting the plot
plt.xticks(df['timestamp'][::10], rotation=45)
plt.title('Persons Count and Sauna Temperature Over Time')
plt.xlabel('Timestamp')
plt.ylabel('Values')
plt.legend()
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()

# Show the plot
plt.show()