import { createApp, ref, watch  } from 'vue'

function time_format(time) {
    return Math.floor(Math.round(time) / 60).toString() +
    ':' +
    (Math.round(time) % 60).toString().padStart(2, '0');
}

const width = 860;
const height = 550;
const marginTop = 20;
const marginRight = 20;
const marginBottom = 30;
const marginLeft = 40;

// Declare the x (horizontal position) scale.
const xScale = d3
    .scaleLinear()
    .domain([-60, 780])
    .range([marginLeft, width - marginRight]);

// Declare the y (vertical position) scale on the left
const yScale = d3
    .scaleLinear()
    .domain([80, 240])
    .range([height - marginBottom, marginTop]);

// Declare the y (vertical position) scale on the right
const yScaleROR = d3
    .scaleLinear()
    .domain([0, 22])
    .range([height - marginBottom, marginTop]);

// Declare the y (vertical position) scale on the right
const yScaleInlet = d3
    .scaleLinear()
    .domain([220, 380])
    .range([height - marginBottom, marginTop]);

// gas chart height 120
const yScaleGas = d3
.scaleLinear()
.domain([0, 100])
.range([height - marginBottom, height - marginBottom - 160]);


// Declare the line generator.
const line = d3.line()
    .x((p) => xScale(p.time))
    .y((p) => yScale(p.value));

const lineROR = d3.line()
    .x((p) => xScale(p.time))
    .y((p) => yScaleROR(p.value));

const lineInlet = d3.line()
    .x((p) => xScale(p.time))
    .y((p) => yScaleInlet(p.value));

const lineGas = d3.line()
    .x((p) => xScale(p.time))
    .y((p) => yScaleGas(p.value))
    .curve(d3.curveStepAfter);

const app = createApp({
    setup() {
        
        let timer = ref("0:00"); 
        let timer_value = ref(0);               
        let gasBubble = ref(20);
        let gasValue = ref(20);

        let showROR = false;

        let toolTipLabels = ref([])

        let store = ref({
            channels: settings.channels.map((c) => ({
              id: c.id,
              color: c.color,
              current_data: 0,
              current_ror: 0,
              data: [],
              ror: [],
              ror_filtered: [],
              ror_smoothed: []
            })),
            
            roast_events: [],
            phases: {
                dry:{time:0, percent:0, temp_rise:0},
                mai:{time:0, percent:0, temp_rise:0},
                dev:{time:0, percent:0, temp_rise:0},
            },
            gas_channel: {}
          });        

        watch(gasValue, (newValue, oldValue) => {
            console.log(newValue);
            socket.emit("gas_value", newValue);
          }
        );
       

        // const socket = io("http://localhost:8000", {
        //   opts: { path: "/socket.io" },
        // });
        const socket = io();

        socket.on("read_device", (channels) => {
            
            store.value.channels = channels;

            // tool tip labels
            let labels=[]

            if(channels[0].data.length > 0) {
                labels.push({
                    label: channels[0].data.at(-1).value.toFixed(1), 
                    x: xScale(channels[0].data.at(-1).time)+2,
                    y: yScale(channels[0].data.at(-1).value)
                })   
            }
            if(channels[1].data.length > 0) {
                labels.push({
                    label: channels[1].data.at(-1).value.toFixed(1), 
                    x: xScale(channels[1].data.at(-1).time)+2,
                    y: yScale(channels[1].data.at(-1).value)
                })   
            }
            if(channels[2].data.length > 0) {
                labels.push({
                    label: channels[2].data.at(-1).value.toFixed(1), 
                    x: xScale(channels[2].data.at(-1).time)+2,
                    y: yScaleInlet(channels[2].data.at(-1).value)
                })   
            }
            if(channels[0].ror_smoothed.length > 0) {
                labels.push({
                    label: channels[0].ror_smoothed.at(-1).value.toFixed(1), 
                    x: xScale(channels[0].ror_smoothed.at(-1).time)+2,
                    y: yScaleROR(channels[0].ror_smoothed.at(-1).value)
                })
            }

            labels.sort((a,b) => a.y-b.y)

            // if labels are too close, add some distance
            for (let i = 0 ; i < labels.length-1 ; i++) {
                if ((labels[i+1].y - labels[i].y) < 10) {
                    labels[i+1].y = labels[i+1].y + 5;
                    labels[i].y = labels[i].y - 5
                }
            }

            toolTipLabels.value = labels
            
        });

        socket.on('update_timer', 
            (t) => { 
             
                timer.value = 
                Math.floor(Math.round(t) / 60).toString() +
                        ':' +
                        (Math.round(t) % 60).toString().padStart(2, '0');

                timer_value.value = t
               
        });

        socket.on("roast_events", (roast_events) => {
            console.log(roast_events);
            store.value.roast_events = roast_events
        });

        socket.on("phases", (phases) => {
            console.log(phases);
            store.value.phases = phases
        });

        socket.on("gas_channel", (gas_channel) => {
            console.log(gas_channel);
            store.value.gas_channel = gas_channel
        });

        return {
            width : width,
            height : height,
            marginTop : marginTop,
            marginRight : marginRight,
            marginBottom : marginBottom,
            marginLeft : marginLeft,
            xScale,
            yScale,
            yScaleROR,
            yScaleInlet,
            yScaleGas,
            line,
            lineROR,
            lineInlet,
            lineGas,
            timer,
            timer_value,
            store,
            gasBubble,
            gasValue,
            showROR,
            toolTipLabels,
            time_format,
            pips: [10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100]
        }
    }
})

// Delimiters changed to ES6 template string style
app.config.compilerOptions.delimiters = ['${', '}']

app.directive(
    'x_axis', (el, binding) => {
        d3.select(el).call(
            d3.axisBottom(xScale)
            .tickValues(d3.range(-60, 780, 60).concat(780))
            .tickFormat(
                (d) => time_format(d)
            )
        );
    }
)

app.directive(
    'y_axis', (el, binding) => {
        d3.select(el).call(d3.axisLeft(yScale));
    }
)

app.directive(
    'y_axis_inlet', (el, binding) => {
        d3.select(el).style("font-size","8px").call(d3.axisRight(yScaleInlet).tickSize(3));
    }
)

app.directive(
    'y_axis_ror', (el, binding) => {
        d3.select(el).call(d3.axisRight(yScaleROR));
    }
)

app.mount('#app')
