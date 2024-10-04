import { createApp, ref, watch  } from 'vue'

function time_format(time) {
    return Math.floor(Math.round(time) / 60).toString() +
    ':' +
    (Math.round(time) % 60).toString().padStart(2, '0');
}

const width = 860;
const height = 650;
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
    .domain([240, 400])
    .range([height - marginBottom, marginTop]);

// gas chart height 120
const yScaleGas = d3
.scaleLinear()
.domain([0, 120])
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
        
        let timer_str = ref("0:00"); 
        let timer = ref(0);               
        let gasBubble = ref(20);
        let gasValue = ref(20);

        let showROR = false;

        let toolTipLabels = ref([])

        let appStatus = ref(appstatus_init)

        let session = ref({
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
            
            roast_events: {},
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

        socket.on("read_device", (s) => {
            console.log(s)

            session.value = s;

            let bt=s.channels[0];
            let et=s.channels[1];
            let inlet=s.channels[2];

            // tool tip labels
            let labels=[]

            if(bt.data.length > 0) {
                labels.push({
                    label: bt.data.at(-1).value.toFixed(1), 
                    x: xScale(bt.data.at(-1).time)+2,
                    y: yScale(bt.data.at(-1).value)
                })   
            }
            if(et.data.length > 0) {
                labels.push({
                    label: et.data.at(-1).value.toFixed(1), 
                    x: xScale(et.data.at(-1).time)+2,
                    y: yScale(et.data.at(-1).value)
                })   
            }
            if(inlet.data.length > 0) {
                labels.push({
                    label: inlet.data.at(-1).value.toFixed(1), 
                    x: xScale(inlet.data.at(-1).time)+2,
                    y: yScaleInlet(inlet.data.at(-1).value)
                })   
            }
            if(bt.ror_smoothed.length > 0) {
                labels.push({
                    label: bt.ror_smoothed.at(-1).value.toFixed(1), 
                    x: xScale(bt.ror_smoothed.at(-1).time)+2,
                    y: yScaleROR(bt.ror_smoothed.at(-1).value)
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
             
                timer_str.value = 
                Math.floor(Math.round(t) / 60).toString() +
                        ':' +
                        (Math.round(t) % 60).toString().padStart(2, '0');

                timer.value = t
               
        });

        socket.on("roast_events", (roast_events) => {
            
            // console.log(roast_events);
            // console.log(Object.keys(roast_events).map((key)=>({id: key, index: roast_events[key]})))
            
            session.value.roast_events = roast_events
        });

        socket.on("app_status", (app_status) => {
            appStatus.value = app_status
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
            timer_str,
            timer,
            appStatus,
            session,
            gasBubble,
            gasValue,
            showROR,
            toolTipLabels,
            socket: socket,
            time_format,
            pips: [10,20,30,40,50,60,70,80,90,100,110,120]
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
