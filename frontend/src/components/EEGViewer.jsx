import { useRef, useEffect, useState } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

// Plugin to draw vertical cursor line on hover
const verticalLinePlugin = {
  id: 'verticalLine',
  afterDraw: (chart) => {
    if (chart.tooltip?._active?.length) {
      const ctx = chart.ctx
      const activePoint = chart.tooltip._active[0]
      const x = activePoint.element.x
      const topY = chart.scales.y.top
      const bottomY = chart.scales.y.bottom

      ctx.save()
      ctx.beginPath()
      ctx.moveTo(x, topY)
      ctx.lineTo(x, bottomY)
      ctx.lineWidth = 1
      ctx.strokeStyle = '#000000'
      ctx.setLineDash([5, 3])
      ctx.stroke()
      ctx.restore()
    }
  }
}

// Register the plugin
ChartJS.register(verticalLinePlugin)

function EEGViewer({ snippet, title }) {
  const chartRef = useRef(null)
  const [channelPositions, setChannelPositions] = useState([])

  // Calculate channel label positions after chart renders
  useEffect(() => {
    if (chartRef.current && snippet) {
      const chart = chartRef.current
      const yScale = chart.scales.y

      if (yScale) {
        const numChannels = snippet.channels.length
        const channelSpacing = 100

        const positions = snippet.channels.map((name, idx) => {
          const offset = (numChannels - 1 - idx) * channelSpacing
          const pixelY = yScale.getPixelForValue(offset)
          return { name, y: pixelY }
        })

        setChannelPositions(positions)
      }
    }
  }, [snippet, chartRef.current?.scales?.y])

  if (!snippet || !snippet.data || snippet.data.length === 0) {
    return (
      <div className="eeg-viewer">
        <div className="eeg-viewer-title">{title || 'EEG Viewer'}</div>
        <div className="no-data">
          <h3>No data available</h3>
          <p>Load an EEG snippet to view</p>
        </div>
      </div>
    )
  }

  const { channels, data, sampling_rate } = snippet
  const numChannels = channels.length
  const numSamples = data[0].length

  // Downsample data for display if too many points
  const maxDisplayPoints = 1000
  const downsampleFactor = Math.max(1, Math.floor(numSamples / maxDisplayPoints))

  // Create time labels
  const timeLabels = []
  for (let i = 0; i < numSamples; i += downsampleFactor) {
    const time = (i / sampling_rate).toFixed(2)
    timeLabels.push(time)
  }

  // Calculate offset for each channel to stack them vertically
  const channelSpacing = 100 // microvolts between channels

  // Prepare datasets - all channels in black
  const datasets = channels.map((channelName, channelIdx) => {
    const channelData = data[channelIdx]
    const offset = (numChannels - 1 - channelIdx) * channelSpacing

    // Downsample and apply offset
    const displayData = []
    for (let i = 0; i < channelData.length; i += downsampleFactor) {
      displayData.push(channelData[i] + offset)
    }

    return {
      label: channelName,
      data: displayData,
      borderColor: '#000000',
      backgroundColor: 'transparent',
      borderWidth: 0.8,
      pointRadius: 0,
      pointHoverRadius: 0,
      tension: 0
    }
  })

  const chartData = {
    labels: timeLabels,
    datasets
  }

  // Calculate y-axis range
  const yMin = -channelSpacing * 0.5
  const yMax = (numChannels - 0.5) * channelSpacing

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    layout: {
      padding: {
        left: 5
      }
    },
    plugins: {
      legend: {
        display: false
      },
      title: {
        display: false
      },
      tooltip: {
        enabled: true,
        mode: 'index',
        intersect: false,
        callbacks: {
          title: (items) => {
            if (items.length > 0) {
              const time = parseFloat(items[0].label).toFixed(2)
              return `Time: ${time}s`
            }
            return ''
          },
          label: () => null
        },
        displayColors: false,
        backgroundColor: 'rgba(0,0,0,0.7)',
        titleFont: { size: 12 },
        padding: 8
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Time (s)',
          color: '#2c3e50',
          font: { size: 11 }
        },
        ticks: {
          maxTicksLimit: 11,
          color: '#2c3e50',
          callback: function(value, index) {
            const time = parseFloat(this.getLabelForValue(value))
            // Skip 0 and 1, show other whole numbers
            if (Math.abs(time - Math.round(time)) < 0.1) {
              const rounded = Math.round(time)
              if (rounded <= 1) return ''
              return rounded
            }
            return ''
          }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.08)'
        }
      },
      y: {
        display: true,
        min: yMin,
        max: yMax,
        title: {
          display: false
        },
        ticks: {
          display: false
        },
        grid: {
          display: false
        }
      }
    },
    interaction: {
      intersect: false,
      mode: 'index'
    },
    hover: {
      mode: 'index',
      intersect: false
    }
  }

  // Force recalculation of positions when chart updates
  const handleChartUpdate = () => {
    if (chartRef.current) {
      const chart = chartRef.current
      const yScale = chart.scales.y

      if (yScale) {
        const positions = channels.map((name, idx) => {
          const offset = (numChannels - 1 - idx) * channelSpacing
          const pixelY = yScale.getPixelForValue(offset)
          return { name, y: pixelY }
        })

        // Only update state if positions actually changed to prevent infinite re-render loop
        setChannelPositions(prev => {
          if (prev.length !== positions.length) return positions
          const changed = positions.some((pos, i) =>
            prev[i]?.name !== pos.name || Math.abs(prev[i]?.y - pos.y) > 0.1
          )
          return changed ? positions : prev
        })
      }
    }
  }

  return (
    <div className="eeg-viewer">
      {title && <div className="eeg-viewer-title">{title}</div>}
      <div className="eeg-chart-wrapper">
        <div className="eeg-y-axis-label">EEG</div>
        <div className="eeg-channel-labels">
          {channelPositions.map((pos, idx) => (
            <div
              key={idx}
              className="channel-label"
              style={{ top: pos.y }}
            >
              {pos.name}
            </div>
          ))}
        </div>
        <div className="eeg-chart-container">
          <Line
            ref={chartRef}
            data={chartData}
            options={options}
            plugins={[{
              id: 'positionUpdater',
              afterRender: handleChartUpdate
            }]}
          />
        </div>
      </div>
    </div>
  )
}

export default EEGViewer
