import 'dart:async';

import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:roastcraft/ticker.dart';

part 'timer_state.dart';

class TimerCubit extends Cubit<TimerState> {
  final Ticker _ticker;
  static const int _maxDuration = 20;

  StreamSubscription<int>? _tickerSubscription;
  TimerCubit({required Ticker ticker})
      : _ticker = ticker,
        super(const TimerState());

  void start() {
    emit(state.copyWith(status: TimerStatus.runInProgress));
    _tickerSubscription?.cancel();
    _tickerSubscription =
        _ticker.tick(ticks: _maxDuration).listen((d) => tick(d));
  }

  void pause() {
    if (state.status == TimerStatus.runInProgress) {
      _tickerSubscription?.pause();
      emit(state.copyWith(status: TimerStatus.runPause));
    }
  }

  void resume() {
    if (state.status == TimerStatus.runPause) {
      _tickerSubscription?.resume();
      emit(state.copyWith(status: TimerStatus.runInProgress));
    }
  }

  void reset() {
    _tickerSubscription?.cancel();
    emit(const TimerState());
  }

  void tick(int d) {
    emit(d < _maxDuration
        ? state.copyWith(duration: d)
        : TimerState(status: TimerStatus.runComplete, duration: d));
  }
}
