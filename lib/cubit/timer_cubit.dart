import 'dart:async';

import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:roastcraft/ticker.dart';

part 'timer_state.dart';

class TimerCubit extends Cubit<TimerState> {
  final Ticker _ticker;
  static const int _initialDuration = 20;

  StreamSubscription<int>? _tickerSubscription;
  TimerCubit({required Ticker ticker})
      : _ticker = ticker,
        super(const TimerState(
            status: TimerStatus.initial, duration: _initialDuration));

  void start() {
    emit(TimerState(
        status: TimerStatus.runInProgress, duration: state.duration));
    _tickerSubscription?.cancel();
    _tickerSubscription =
        _ticker.tick(ticks: state.duration).listen((d) => tick(d));
  }

  void pause() {
    if (state.status == TimerStatus.runInProgress) {
      _tickerSubscription?.pause();
      emit(TimerState(status: TimerStatus.runPause, duration: state.duration));
    }
  }

  void resume() {
    if (state.status == TimerStatus.runPause) {
      _tickerSubscription?.resume();
      emit(TimerState(
          status: TimerStatus.runInProgress, duration: state.duration));
    }
  }

  void reset() {
    _tickerSubscription?.cancel();
    emit(const TimerState(
        status: TimerStatus.initial, duration: _initialDuration));
  }

  void tick(int d) {
    emit(d > 0
        ? TimerState(status: TimerStatus.runInProgress, duration: d)
        : const TimerState(status: TimerStatus.runComplete, duration: 0));
  }
}
