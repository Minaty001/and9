"""
Verify all Phase 21-40 services via direct asyncio.run() to bypass pytest-asyncio hang.
"""
import asyncio
import sys
sys.path.insert(0, '.')


async def test_phase21():
    from services.phase21_api import ApiManagerService, ApiRequest, ApiResponse
    from services.phase21_api.adapter import MockHttpAdapter
    svc = ApiManagerService()
    assert await svc.initialize() == True
    health = await svc.health()
    assert health['status'] == 'healthy'
    adapter = MockHttpAdapter()
    resp = ApiResponse(success=True, status_code=200, data={'msg': 'hello'})
    adapter.register_response('/api/hello', resp)
    svc.register_adapter('test', adapter)
    result = await svc.execute(ApiRequest(endpoint='/api/hello', adapter_name='test'))
    assert result.success and result.data == {'msg': 'hello'}
    assert 'test' in svc.list_adapters()
    # Test fallback
    adapter1 = MockHttpAdapter(name='primary')
    adapter1.register_response('/api/data', ApiResponse(success=False, status_code=500))
    adapter2 = MockHttpAdapter(name='fallback')
    adapter2.register_response('/api/data', ApiResponse(success=True, data='from_fallback'))
    svc.register_adapter('primary', adapter1)
    svc.register_adapter('fallback', adapter2)
    result = await svc.execute(ApiRequest(endpoint='/api/data', adapter_name='primary'))
    assert result.success and result.data == 'from_fallback'
    await svc.shutdown()
    return 'Phase 21 OK'


async def test_phase22():
    from services.phase22_realtime import RealtimeInfoService, InfoRequest
    svc = RealtimeInfoService()
    assert await svc.initialize() == True
    health = await svc.health()
    assert health['status'] == 'healthy'
    # Test time provider
    results = await svc.fetch(InfoRequest(query='time in London', source_types=['time']))
    assert len(results) > 0
    assert results[0].source == 'time'
    assert not results[0].cache_hit
    # Test weather
    results2 = await svc.fetch(InfoRequest(query='weather in London', source_types=['weather']))
    assert len(results2) > 0
    assert results2[0].source == 'weather'
    # Test cache
    results3 = await svc.fetch(InfoRequest(query='weather in London', source_types=['weather']))
    assert results3[0].cache_hit
    await svc.shutdown()
    return 'Phase 22 OK'


async def test_phase23():
    from services.phase23_voice import VoiceControllerService
    svc = VoiceControllerService()
    assert await svc.initialize() == True
    health = await svc.health()
    assert health['status'] == 'healthy'
    # Test STT
    result = await svc.recognize('', language='en-IN')
    assert result.transcript and result.confidence > 0
    assert not result.is_final
    # Test TTS
    tts = await svc.synthesize('Hello world', language='en-IN')
    assert tts.text_synthesized == 'Hello world'
    assert tts.audio_data and tts.format == 'wav'
    # Test state
    state = await svc.get_state()
    assert state.status == 'idle'
    await svc.set_language('hi-IN')
    assert (await svc.get_state()).language == 'hi-IN'
    await svc.shutdown()
    return 'Phase 23 OK'


async def test_phase24():
    from services.phase24_conversation import ConversationManagerService
    svc = ConversationManagerService()
    assert await svc.initialize() == True
    # Test session management
    session = await svc.create_session()
    assert session.id and session.active
    # Test process turn
    state = await svc.process_turn(session.id, 'what is the weather', intent='query', entities={'topic': 'weather'})
    assert state.active_topic == 'weather'
    # Test reference resolution
    resolved = await svc.resolve_reference('it', session.id)
    assert resolved  # should resolve based on context
    # Test get state
    got = await svc.get_state(session.id)
    assert got.active_topic == 'weather'
    # Test end session
    await svc.end_session(session.id)
    assert len(await svc.get_active_sessions()) == 0
    await svc.shutdown()
    return 'Phase 24 OK'


async def test_phase25():
    from services.phase25_personality import PersonalityEngineService
    svc = PersonalityEngineService()
    assert await svc.initialize() == True
    # Test built-in personas
    personas = await svc.list_personas()
    assert len(personas) >= 3
    assert 'jarvis_default' in personas
    # Test apply tone
    result = await svc.apply_tone('Hello there!', persona_id='jarvis_default')
    # Test greeting
    greeting = await svc.generate_greeting(context={'hour': 9})
    assert greeting
    # Test constrain response
    constrained = await svc.constrain_response('A very long response ' * 100)
    assert len(constrained) <= 500
    # Test persona switching
    assert await svc.set_persona('jarvis_casual') == True
    current = await svc.get_persona()
    assert current.name == 'jarvis_casual'
    # Test detect tone
    tone = await svc.detect_tone('Please help me with this')
    assert tone
    await svc.shutdown()
    return 'Phase 25 OK'


async def test_phase26():
    from services.phase26_learning import LearningEngineService
    svc = LearningEngineService()
    assert await svc.initialize() == True
    # Test observe preference
    pref = await svc.observe('preference', 'language', 'python', {'context': 'coding'})
    assert pref.category == 'preference'
    # Test get preference
    got = await svc.get_preference('preference', 'language')
    assert got is not None and got.preferred_value == 'python'
    # Test pattern recording
    await svc.record_pattern('test_pattern', 'greeting', {'time': 'morning'})
    matches = await svc.find_patterns({'time': 'morning'})
    assert any(p.trigger == 'test_pattern' for p in matches)
    # Test summarization
    summary = await svc.generate_summary('daily')
    assert summary.period == 'daily'
    assert summary.total_interactions >= 0
    await svc.forget_preference('preference', 'language')
    assert await svc.get_preference('preference', 'language') is None
    await svc.shutdown()
    return 'Phase 26 OK'


async def test_phase27():
    from services.phase27_knowledge import KnowledgeBaseService
    svc = KnowledgeBaseService()
    assert await svc.initialize() == True
    # Test add
    entry = await svc.add_knowledge('What is AI?', 'Artificial Intelligence', 'tech', ['ai', 'ml'])
    assert entry.id
    # Test query
    results = await svc.query('What is AI?')
    assert results.total_found > 0
    assert results.entries[0].answer == 'Artificial Intelligence'
    # Test get by tag
    tagged = await svc.get_by_tag('ai')
    assert len(tagged) > 0
    # Test export/import
    data = await svc.export_data()
    assert isinstance(data, list)
    # Test stats
    stats = await svc.stats()
    assert stats['total_entries'] >= 1
    await svc.shutdown()
    return 'Phase 27 OK'


async def test_phase28():
    from services.phase28_scheduler import SchedulerService
    from datetime import datetime, timedelta, timezone
    svc = SchedulerService()
    assert await svc.initialize() == True
    # Test schedule
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    item_id = await svc.schedule('Test reminder', future, tags=['test'])
    assert item_id
    # Test get upcoming
    upcoming = await svc.get_upcoming()
    assert len(upcoming) > 0
    # Test parse time
    parsed = await svc.parse_time('in 5 minutes')
    assert parsed.confidence > 0
    # Test cancel
    assert await svc.cancel(item_id) == True
    # Test create reminder
    reminder_id = await svc.create_reminder('Meeting', 'tomorrow at 3pm')
    assert reminder_id
    await svc.dismiss(reminder_id)
    await svc.shutdown()
    return 'Phase 28 OK'


async def test_phase29():
    from services.phase29_automation import AutomationService
    svc = AutomationService()
    assert await svc.initialize() == True
    # Test create rule
    rule = await svc.create_rule(
        'Morning Greeting',
        trigger={'type': 'time', 'params': {'hour': 9}},
        actions=[{'type': 'notify', 'params': {'message': 'Good morning!'}}]
    )
    assert rule and rule.id
    # Test get rule
    got = await svc.get_rule(rule.id)
    assert got.name == 'Morning Greeting'
    # Test list rules
    rules = await svc.list_rules()
    assert len(rules) >= 1
    # Test enable/disable
    assert await svc.disable_rule(rule.id) == True
    assert not (await svc.get_rule(rule.id)).isenabled
    # Test execution history
    history = await svc.get_execution_history()
    assert isinstance(history, list)
    await svc.shutdown()
    return 'Phase 29 OK'


async def test_phase30():
    from services.phase30_notification import NotificationManagerService
    svc = NotificationManagerService()
    assert await svc.initialize() == True
    # Test send notification
    nid = await svc.send_notification('Test Title', 'Test Message', priority='high')
    assert nid
    # Test get notifications
    notifs = await svc.get_notifications()
    assert len(notifs) == 1
    assert notifs[0].title == 'Test Title'
    # Test mark read
    await svc.mark_read(nid)
    assert (await svc.get_notifications())[0].is_read
    # Test templates
    await svc.register_template('welcome', 'Welcome {name}!', 'Hello {name}, welcome!')
    title, msg = await svc.render_template('welcome', {'name': 'John'})
    assert title == 'Welcome John!'
    # Test dismiss
    await svc.dismiss(nid)
    assert len(await svc.get_notifications()) == 0
    await svc.shutdown()
    return 'Phase 30 OK'


async def test_phase31():
    from services.phase31_security import SecurityService
    svc = SecurityService()
    assert await svc.initialize() == True
    # Test validate
    result = await svc.validate('hello world')
    assert result.is_valid
    assert result.risk_score < 0.5
    # Test validate dangerous
    dangerous = await svc.validate("DROP TABLE users;")
    assert not dangerous.is_valid
    # Test sanitize
    clean = await svc.sanitize('<script>alert("xss")</script>')
    assert '<script>' not in clean
    # Test auth
    token = await svc.generate_token('user1')
    assert await svc.authenticate(token) == True
    assert await svc.get_user_id(token) == 'user1'
    # Test encrypt/decrypt
    ct, iv = await svc.encrypt('secret data')
    decrypted = await svc.decrypt(ct, iv)
    assert decrypted == 'secret data'
    await svc.shutdown()
    return 'Phase 31 OK'


async def test_phase32():
    from services.phase32_permissions import PermissionManagerService
    svc = PermissionManagerService()
    assert await svc.initialize() == True
    # Create role
    await svc.create_role('editor', 'Editor role', permissions=['read', 'write'])
    # Assign role
    await svc.assign_role('user1', 'editor')
    # Test permission check
    result = await svc.has_permission('user1', 'documents', 'read')
    assert result.is_granted
    result2 = await svc.has_permission('user1', 'documents', 'delete')
    assert not result2.is_granted
    # Test list roles
    roles = await svc.list_roles()
    assert 'editor' in roles
    # Test remove role
    await svc.remove_role('user1', 'editor')
    result3 = await svc.has_permission('user1', 'documents', 'read')
    assert not result3.is_granted
    await svc.shutdown()
    return 'Phase 32 OK'


async def test_phase33():
    from services.phase33_error_recovery import ErrorRecoveryService
    svc = ErrorRecoveryService()
    assert await svc.initialize() == True
    # Test analyze error
    analysis = await svc.analyze_error(ValueError('invalid input'))
    assert analysis['error_type'] in ('validation', 'unknown')
    # Test execute with recovery
    def failing_op():
        raise ConnectionError('connection failed')
    success, result, action = await svc.execute_with_recovery(
        failing_op, service_name='test', operation='connect'
    )
    assert not success
    assert action in ('retry', 'fallback', 'degrade')
    # Test circuit breaker
    status = await svc.get_circuit_breaker_status()
    assert isinstance(status, list) or isinstance(status, dict)
    # Test reset
    await svc.reset_circuit_breaker()
    await svc.shutdown()
    return 'Phase 33 OK'


async def test_phase34():
    from services.phase34_logging import LoggingService
    svc = LoggingService()
    assert await svc.initialize() == True
    # Test log
    await svc.info('test_service', 'Test message')
    await svc.warn('test_service', 'Warning message')
    await svc.error('test_service', 'Error message')
    # Test query
    results = await svc.query_logs(level='INFO')
    assert len(results.entries) > 0
    assert results.entries[0].message == 'Test message'
    # Test set level
    await svc.set_level('ERROR')
    # Test flush
    await svc.flush()
    await svc.shutdown()
    return 'Phase 34 OK'


async def test_phase35():
    from services.phase35_analytics import AnalyticsService
    svc = AnalyticsService()
    assert await svc.initialize() == True
    # Track events
    await svc.track_event('user_action', 'session1', category='ui', action='click')
    await svc.track_event('page_view', 'session1', category='ui', action='view')
    # Record metrics
    await svc.record_metric('response_time', 150, tags={'endpoint': '/api'})
    await svc.record_metric('response_time', 200, tags={'endpoint': '/api'})
    # Test event count
    count = await svc.get_event_count('user_action')
    assert count >= 1
    # Test generate report
    report = await svc.generate_report('daily')
    assert report.report_type == 'daily'
    assert report.metrics is not None
    # Test metric timeseries
    timeseries = await svc.get_metric_timeseries('response_time')
    assert len(timeseries) >= 1
    await svc.shutdown()
    return 'Phase 35 OK'


async def test_phase36():
    from services.phase36_database import DatabaseService
    svc = DatabaseService()
    assert await svc.initialize() == True
    # Insert
    doc_id = await svc.insert('test_collection', {'name': 'Alice', 'age': 30, 'email': 'a@b.com'})
    assert doc_id
    # Find
    results = await svc.find('test_collection', {'name': 'Alice'})
    assert len(results) >= 1
    # Find one
    doc = await svc.find_one('test_collection', {'name': 'Alice'})
    assert doc['name'] == 'Alice'
    # Update
    assert await svc.update('test_collection', doc_id, {'age': 31}) == True
    doc2 = await svc.find_one('test_collection', {'name': 'Alice'})
    assert doc2['age'] == 31
    # Delete
    assert await svc.delete('test_collection', doc_id) == True
    assert await svc.find_one('test_collection', {'name': 'Alice'}) is None
    await svc.shutdown()
    return 'Phase 36 OK'


async def test_phase37():
    from services.phase37_file_manager import FileManagerService
    svc = FileManagerService()
    assert await svc.initialize() == True
    # Create file
    item = await svc.create_file('/test/hello.txt', 'Hello World')
    assert item.name == 'hello.txt'
    # Read file
    content = await svc.read_file('/test/hello.txt')
    assert content == 'Hello World'
    # List dir
    listing = await svc.list_directory('/test')
    assert listing.entry_count >= 1
    # Copy
    assert await svc.copy('/test/hello.txt', '/test/hello2.txt') == True
    # Move
    assert await svc.move('/test/hello2.txt', '/test/moved.txt') == True
    # Trash
    assert await svc.move_to_trash('/test/moved.txt') == True
    trashed = await svc.list_trash()
    assert len(trashed) >= 1
    await svc.empty_trash()
    assert len(await svc.list_trash()) == 0
    # Get info
    info = await svc.get_info('/test/hello.txt')
    assert info.size_bytes == len('Hello World')
    await svc.shutdown()
    return 'Phase 37 OK'


async def test_phase38():
    from services.phase38_config import ConfigService
    svc = ConfigService()
    assert await svc.initialize() == True
    # Set config
    await svc.set_config('app.name', 'JARVIS')
    await svc.set_config('app.version', '3.0')
    # Get config
    assert await svc.get_config('app.name') == 'JARVIS'
    assert await svc.get_config('app.version') == '3.0'
    assert await svc.get_config('nonexistent', 'default') == 'default'
    # Has
    assert await svc.has_config('app.name') == True
    # Get all
    all_config = await svc.get_all_config()
    assert 'app.name' in all_config
    # Profiles
    await svc.create_profile('production')
    assert 'production' in await svc.list_profiles()
    await svc.activate_profile('production')
    assert await svc.get_active_profile() == 'production'
    # Delete
    await svc.delete_config('app.name')
    assert await svc.has_config('app.name') == False
    await svc.shutdown()
    return 'Phase 38 OK'


async def test_phase39():
    from services.phase39_plugin_sdk import PluginSdkService
    svc = PluginSdkService()
    assert await svc.initialize() == True
    # Discover plugins
    discovered = await svc.discover_plugins()
    assert isinstance(discovered, list)
    # Load (should be none since no real plugins)
    loaded = await svc.get_loaded_plugins()
    assert isinstance(loaded, list)
    # Register hook
    await svc.register_hook('on_initialize', 'test_plugin', lambda ctx: None)
    hooks = await svc.get_hooks('on_initialize')
    assert len(hooks) >= 1
    # Execute hooks
    results = await svc.execute_hooks('on_initialize', {'service': 'test'})
    assert isinstance(results, list)
    await svc.shutdown()
    return 'Phase 39 OK'


async def test_phase40():
    from services.phase40_performance import PerformanceOptimizerService
    svc = PerformanceOptimizerService()
    assert await svc.initialize() == True

    # Test L1 cache
    await svc.l1_set('key1', 'value1')
    val, hit = await svc.l1_get('key1')
    assert val == 'value1'
    assert hit == True

    # Test L2 cache
    await svc.l2_set('key2', 'value2')
    val2, hit2 = await svc.l2_get('key2')
    assert val2 == 'value2'
    assert hit2 == True

    # Test request coalescing
    import time
    async def slow_op():
        await asyncio.sleep(0.05)
        return 'result'
    
    results = await asyncio.gather(
        svc.coalesce('same_key', slow_op),
        svc.coalesce('same_key', slow_op),
        svc.coalesce('same_key', slow_op),
    )
    assert all(r == 'result' for r in results)

    # Test resource pool
    resource, rid = await svc.pool_acquire()
    assert resource is not None
    assert rid is not None
    await svc.pool_release(rid)

    # Stats
    stats = await svc.get_detailed_stats()
    assert 'l1_cache' in stats
    assert 'l2_cache' in stats
    assert 'resource_pool' in stats

    await svc.shutdown()
    return 'Phase 40 OK'


async def main():
    tests = [
        test_phase21, test_phase22, test_phase23, test_phase24, test_phase25,
        test_phase26, test_phase27, test_phase28, test_phase29, test_phase30,
        test_phase31, test_phase32, test_phase33, test_phase34, test_phase35,
        test_phase36, test_phase37, test_phase38, test_phase39, test_phase40,
    ]
    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            result = await test_fn()
            print(f'  ✅ {result}')
            passed += 1
        except Exception as e:
            print(f'  ❌ {test_fn.__name__}: {e}')
            import traceback
            traceback.print_exc()
            failed += 1
    print(f'\nResults: {passed} passed, {failed} failed out of {len(tests)} phases')

if __name__ == '__main__':
    asyncio.run(main())
